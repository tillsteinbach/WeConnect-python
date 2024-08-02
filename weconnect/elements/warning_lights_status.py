from enum import Enum
import base64
import io
import logging

from weconnect.addressable import AddressableAttribute, AddressableObject, AddressableDict
from weconnect.elements.generic_status import GenericStatus

SUPPORT_IMAGES = False
try:
    from PIL import Image  # type: ignore
    SUPPORT_IMAGES = True
except ImportError:
    pass

LOG = logging.getLogger("weconnect")


class WarningLightsStatus(GenericStatus):
    def __init__(
        self,
        vehicle,
        parent,
        statusId,
        fromDict=None,
        fixAPI=True,
    ):
        self.mileage_km = AddressableAttribute(localAddress='mileage_km', value=None, parent=self, valueType=int)
        self.warningLights = AddressableDict(localAddress='warningLights', parent=self)
        super().__init__(vehicle=vehicle, parent=parent, statusId=statusId, fromDict=fromDict, fixAPI=fixAPI)

    def update(self, fromDict, ignoreAttributes=None):
        ignoreAttributes = ignoreAttributes or []
        LOG.debug('Update warning lights status from dict')

        if 'value' in fromDict:
            if 'mileage_km' in fromDict['value']:
                mileage_km = int(fromDict['value']['mileage_km'])
                if self.fixAPI and mileage_km == 0x7FFFFFFF:
                    mileage_km = None
                    LOG.info('%s: Attribute mileage_km was error value 0x7FFFFFFF. Setting error state instead'
                             ' of 2147483647 km.', self.getGlobalAddress())
                self.mileage_km.setValueWithCarTime(mileage_km, lastUpdateFromCar=None, fromServer=True)
            else:
                self.mileage_km.enabled = False

            if 'warningLights' in fromDict['value'] and fromDict['value']['warningLights'] is not None:
                for warningLightDict in fromDict['value']['warningLights']:
                    if 'messageId' in warningLightDict:
                        if warningLightDict['messageId'] in self.warningLights:
                            self.warningLights[warningLightDict['messageId']].update(fromDict=warningLightDict)
                        else:
                            self.warningLights[warningLightDict['messageId']] = WarningLightsStatus.WarningLight(fromDict=warningLightDict,
                                                                                                                 parent=self.warningLights)
                for warningLightMessageId in [warningLightMessageId for warningLightMessageId in self.warningLights.keys()
                                              if warningLightMessageId not in [warningLight['messageId'] for warningLight in fromDict['value']['warningLights']
                                                                               if 'messageId' in warningLight]]:
                    del self.warningLights[warningLightMessageId]
            else:
                self.warningLights.clear()
                self.warningLights.enabled = False
        else:
            self.mileage_km.enabled = False
            self.warningLights.clear()
            self.warningLights.enabled = False

        super().update(fromDict=fromDict, ignoreAttributes=(ignoreAttributes
                                                            + [
                                                                'mileage_km',
                                                                'warningLights',
                                                            ]))

    def __str__(self):
        string = super().__str__()
        if self.mileage_km.enabled:
            string += f'\n\tCurrent milage: {self.mileage_km.value} km'
        if self.warningLights.enabled and len(self.warningLights) > 0:
            string += f'\n\tWarning Lights: {len(self.warningLights)} items'
            for warningLight in self.warningLights.values():
                string += '\n' + ''.join(['\t\t' + line for line in str(warningLight).splitlines(True)])
        return string

    class WarningLight(AddressableObject):
        def __init__(
            self,
            parent,
            fromDict=None,
        ):
            super().__init__(localAddress=None, parent=parent)
            self.text = AddressableAttribute(localAddress='text', parent=self, value=None, valueType=str)
            self.category = AddressableAttribute(localAddress='category', parent=self, value=None, valueType=WarningLightsStatus.WarningLight.Category)
            self.priority = AddressableAttribute(localAddress='priority', parent=self, value=None, valueType=int)
            self.icon = AddressableAttribute(localAddress='icon', parent=self, value=None, valueType=Image.Image)
            self.iconName = AddressableAttribute(localAddress='iconName', parent=self, value=None, valueType=str)
            self.iconColor = AddressableAttribute(localAddress='iconColor', parent=self, value=None, valueType=WarningLightsStatus.WarningLight.IconColor)
            self.messageId = AddressableAttribute(localAddress='messageId', parent=self, value=None, valueType=str)
            self.notificationId = AddressableAttribute(localAddress='notificationId', parent=self, value=None, valueType=int)
            self.serviceLead = AddressableAttribute(localAddress='serviceLead', parent=self, value=None, valueType=bool)
            self.customerRelevance = AddressableAttribute(localAddress='customerRelevance', parent=self, value=None, valueType=bool)

            if fromDict is not None:
                self.update(fromDict)

        def update(self, fromDict):
            LOG.debug('Update warning light from dict')

            if 'messageId' in fromDict:
                self.messageId.fromDict(fromDict, 'messageId')
                self.localAddress = self.messageId.value
            else:
                LOG.error('Warning light is missing messageId attribute')

            self.text.fromDict(fromDict, 'text')
            self.category.fromDict(fromDict, 'category')
            self.priority.fromDict(fromDict, 'priority')
            self.notificationId.fromDict(fromDict, 'notificationId')
            if SUPPORT_IMAGES:
                if 'icon' in fromDict and fromDict['icon'] is not None:
                    prefix = 'data:image/png;base64,'
                    if fromDict['icon'].startswith(prefix):
                        img = fromDict['icon'][len(prefix):]
                        img = base64.b64decode(img)
                        img = Image.open(io.BytesIO(img))
                        self.icon.setValueWithCarTime(img, lastUpdateFromCar=None, fromServer=True)
                    else:
                        LOG.error('%s: warning light icon is not a base64 encoded png', self.getGlobalAddress())
                        self.icon.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
                        self.icon.enabled = False
                else:
                    self.icon.setValueWithCarTime(None, lastUpdateFromCar=None, fromServer=True)
                    self.icon.enabled = False

            self.iconName.fromDict(fromDict, 'iconName')
            self.iconColor.fromDict(fromDict, 'iconColor')
            self.serviceLead.fromDict(fromDict, 'serviceLead')
            self.customerRelevance.fromDict(fromDict, 'customerRelevance')

            for key, value in {key: value for key, value in fromDict.items() if key not in ['messageId', 'category', 'priority', 'icon', 'iconName',
                                                                                            'serviceLead', 'customerRelevance', 'text',
                                                                                            'notificationId', 'iconColor']}.items():
                LOG.warning('%s: Unknown attribute %s with value %s', self.getGlobalAddress(), key, value)

        def __str__(self):
            returnStr = f'{self.messageId.value}: {self.text.value}'  # pylint: disable=no-member
            if self.category.enabled:
                returnStr += f'\n\tCategory: {self.category.value.value}'
            if self.priority.enabled:
                returnStr += f'\n\tPriority: {self.priority.value}'
            if self.customerRelevance.enabled:
                returnStr += f'\n\tCustomer Relevance: {self.customerRelevance.value}'
            if self.serviceLead.enabled:
                returnStr += f'\n\tService Lead: {self.serviceLead.value}'
            return returnStr

        class Category(Enum,):
            LIGHTING = 'LIGHTING'
            TIRE = 'TIRE'
            ENGINE = 'ENGINE'
            OTHER = 'OTHER'
            UNKNOWN = 'unknown category'

        class IconColor(Enum,):
            YELLOW = 'Yellow'
            RED = 'Red'
            ICON_NOT_FOUND = 'ICON_NOT_FOUND'
            UNKNOWN = 'unknown color'
