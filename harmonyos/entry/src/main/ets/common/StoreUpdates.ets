import { common } from '@kit.AbilityKit';
import { updateManager } from '@kit.AppGalleryKit';

// Set true only for a signed release already published in AppGallery.
const STORE_RELEASED: boolean = false;

export async function checkStoreUpdate(context: common.UIAbilityContext): Promise<string> {
  if (!STORE_RELEASED) {
    return '当前为开发版本，尚未在华为应用市场上架，应用内更新暂不可用。';
  }
  if (!canIUse('SystemCapability.AppGalleryService.Distribution.Update')) {
    return '当前设备不支持应用市场更新服务。';
  }
  const result = await updateManager.checkAppUpdate(context);
  if (result.updateAvailable === updateManager.UpdateAvailableCode.LATER_VERSION_EXIST) {
    const shown = await updateManager.showUpdateDialog(context);
    return `已调用系统更新提示，结果码：${shown}。请按系统提示完成更新。`;
  }
  if (result.updateAvailable === updateManager.UpdateAvailableCode.LATER_VERSION_NOT_EXIST) {
    return '当前已是应用市场最新版本。';
  }
  return `未能确认是否存在更新，结果码：${result.updateAvailable}。`;
}
