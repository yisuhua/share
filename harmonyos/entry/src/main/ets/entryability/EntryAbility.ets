import { UIAbility } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';
import { hilog } from '@kit.PerformanceAnalysisKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { systemBall } from '../common/SystemBall';

export default class EntryAbility extends UIAbility {
  onWindowStageCreate(stage: window.WindowStage): void {
    stage.loadContent('pages/Index', (error: BusinessError) => {
      if (error.code) {
        hilog.error(0x0000, 'Share', 'Load page failed: %{public}d', error.code);
      }
    });
  }

  onDestroy(): void {
    systemBall.stop().catch((error: BusinessError) => {
      hilog.error(0x0000, 'Share', 'Stop ball failed: %{public}d', error.code);
    });
  }
}
