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
                "skins": [{"name": "default", "attachment": {}}],
                "animations": {}
            }
            self.spineBones = self.json['bones']
            self.spineSlots = self.json['slots']
            self.spineSkins = self.json['skins']

            Krita.instance().setBatchmode(True)
            self.document = document
            self.setRootPosition()
            self._export(document.rootNode(), self.directory, xOffset=self.x, yOffset=self.y)
            Krita.instance().setBatchmode(False)
            with open('{0}/{1}'.format(self.directory, 'spine.json'), 'w') as outfile:
                json.dump(self.json, outfile, indent=2)
            self._alert("Export Successful")
        else:
            self._alert("Please select a Document")
    
    def getSkin(self, skinName):
        for skin in self.spineSkins:
            if skin['name'] == skinName:
                return skin
        return self.spineSkins[0]
        
    def getBone(self, boneName):
        for bone in self.spineBones:
            if bone['name'] == boneName:
                return bone
        return self.spineBones[0]
        
    def isBoneExist(self, boneName):
        for bone in self.spineBones:
            if bone['name'] == boneName:
                return True
        return False
        
    def isSlotExist(self, slotName):
        for slot in self.spineSlots:
            if slot['name'] == slotName:
                return True
        return False
        
    def createDirectoy(self, name):
        if not os.path.exists(self.directory+"/"+name):
            os.makedirs(self.directory+"/"+name)

    def setRootPosition(self):
        y = self.document.horizontalGuides()
        x = self.document.verticalGuides()
        if len(y) > 0 and len(x) > 0:
            self.y = -y[0]
            self.x = x[0]
        else:
            self.y = 0
            self.x = 0

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
                        newBoneDict = {
                            'name': newBone,
                            'parent': bone,
                            'x': newX,
                            'y': newY
                        }
                        # if newSkin != 'default':
                            # newBoneDict['skin'] = True
                        
                        if self.isBoneExist(newBone) == False:
                            self.spineBones.append(newBoneDict)
                            newX = xOffset + newX
                            newY = yOffset + newY
                        else:
                            c_bone = self.getBone(newBone)
                            newX = xOffset + c_bone['x']
                            newY = yOffset + c_bone['y']
                            
                    if self.slotPattern.search(child.name()):
                        newSlotName = self.slotPattern.sub('', child.name()).strip()
                        newSlot = {
                            'name': newSlotName,
                            'bone': bone,
                            'attachment': None,
                        }
                        if self.isSlotExist(newSlotName) == False:
                            self.spineSlots.append(newSlot)
                           
                    if self.skinPattern.search(child.name()):
                        newSkin = self.skinPattern.sub('', child.name()).strip()
                        self.spineSkins.append({
                            'name': newSkin,
                            'attachments':{}
                        })
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
                if self.isSlotExist(name) == False:
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
            if slotName not in skinDict['attachments']:
                skinDict['attachments'][slotName] = {}
            skinDict['attachments'][slotName][name] = {
                'name': nameDir+name,
                'x': rect.left() + rect.width() / 2 - xOffset,
                'y': (- rect.bottom() + rect.height() / 2) - yOffset,
                'rotation': 0,
                'width': rect.width(),
                'height': rect.height(),
            }


# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(SpineExport(Krita.instance()))

