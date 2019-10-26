import os
import json
import re

from PyQt5.QtWidgets import (QFileDialog, QMessageBox)

from krita import (Krita, Extension, InfoObject)


class SpineExport(Extension):

    def __init__(self, parent):
        super().__init__(parent)
        self.directory = None
        self.msgBox = None
        self.fileFormat = 'png'
        self.bonePattern = re.compile("\(bone\)|\[bone\]", re.IGNORECASE)
        self.mergePattern = re.compile("\(merge\)|\[merge\]", re.IGNORECASE)
        self.slotPattern = re.compile("\(slot\)|\[slot\]", re.IGNORECASE)
        self.skinPattern = re.compile("\(skin\)|\[skin\]", re.IGNORECASE)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("SpineExport", "Export to Spine", "tools/scripts")
        action.triggered.connect(self.exportDocument)

    def exportDocument(self):
        document = Krita.instance().activeDocument()

        if document is not None:
            if not self.directory:
                self.directory = os.path.dirname(document.fileName()) if document.fileName() else os.path.expanduser("~")
            self.directory = QFileDialog.getExistingDirectory(None, "Select a folder", self.directory, QFileDialog.ShowDirsOnly)

            if not self.directory:
                self._alert('Abort!')
                return

            self.json = {
                "skeleton": {"images": self.directory},
                "bones": [{"name": "root"}],
                "slots": [],
                "skins": {"default": {}},
                "animations": {}
            }
            self.spineBones = self.json['bones']
            self.spineSlots = self.json['slots']
            self.spineSkins = self.json['skins']

            Krita.instance().setBatchmode(True)
            self.document = document
            self._export(document.rootNode(), self.directory)
            Krita.instance().setBatchmode(False)
            with open('{0}/{1}'.format(self.directory, 'spine.json'), 'w') as outfile:
                json.dump(self.json, outfile, indent=2)
            self._alert("Export Successful")
        else:
            self._alert("Please select a Document")
    
    def getSkin(self, skinName):
        return self.spineSkins[skinName]
        
    def createDirectoy(self, name):
        if not os.path.exists(self.directory+"/"+name):
            os.makedirs(self.directory+"/"+name)
        

    def _alert(self, message):
        self.msgBox = self.msgBox if self.msgBox else QMessageBox()
        self.msgBox.setText(message)
        self.msgBox.exec_()

    def _export(self, node, directory, bone="root", xOffset=0, yOffset=0, slot=None, skin="default"):
        for child in node.childNodes():
            if "selectionmask" in child.type():
                continue

            if not child.visible():
                continue

            if '(ignore)' in child.name():
                continue

            if child.childNodes():
                if not self.mergePattern.search(child.name()):
                    newSkin = skin
                    newBone = bone
                    newSlot = slot
                    newX = xOffset
                    newY = yOffset
                    if self.bonePattern.search(child.name()):
                        newBone = self.bonePattern.sub('', child.name()).strip()
                        rect = child.bounds()
                        newX = rect.left() + rect.width() / 2 - xOffset
                        newY = (- rect.bottom() + rect.height() / 2) - yOffset
                        self.spineBones.append({
                            'name': newBone,
                            'parent': bone,
                            'x': newX,
                            'y': newY
                        })
                        newX = xOffset + newX
                        newY = yOffset + newY
                    if self.slotPattern.search(child.name()):
                        newSlotName = self.slotPattern.sub('', child.name()).strip()
                        newSlot = {
                            'name': newSlotName,
                            'bone': bone,
                            'attachment': None,
                        }
                        self.spineSlots.append(newSlot)
                           
                    if self.skinPattern.search(child.name()):
                        newSkin = self.skinPattern.sub('', child.name()).strip()
                        self.spineSkins[newSkin] = {}
                        self.createDirectoy(newSkin)

                    self._export(child, directory, newBone, newX, newY, newSlot, newSkin)
                    continue

            saveDir = directory
            if skin != "default":
                saveDir = directory+"/"+skin
            name = self.mergePattern.sub('', child.name()).strip()
            layerFileName = '{0}/{1}.{2}'.format(saveDir, name, self.fileFormat)
            child.save(layerFileName, 96, 96, InfoObject())

            newSlot = slot
            if not newSlot:
                newSlot = {
                    'name': name,
                    'bone': bone,
                    'attachment': name,
                }
                self.spineSlots.append(newSlot)
            else:
                if not newSlot['attachment']:
                    newSlot['attachment'] = name

            rect = child.bounds()
            slotName = newSlot['name']
            skinDict = self.getSkin(skin)
            nameDir = ""
            if skin != "default":
                nameDir = skin+"/"
            if slotName not in skinDict:
                skinDict[slotName] = {}
            skinDict[slotName][name] = {
                'name': nameDir+name,
                'x': rect.left() + rect.width() / 2 - xOffset,
                'y': (- rect.bottom() + rect.height() / 2) - yOffset,
                'rotation': 0,
                'width': rect.width(),
                'height': rect.height(),
            }


# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(SpineExport(Krita.instance()))

