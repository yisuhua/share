import { common } from '@kit.AbilityKit';
import { floatingBall } from '@kit.ArkUI';
import { BusinessError } from '@kit.BasicServicesKit';

class SystemBall {
  private controller: floatingBall.FloatingBallController | undefined = undefined;
  private started: boolean = false;
  private notify: (message: string) => void = () => {};

  async start(context: common.UIAbilityContext, notify: (message: string) => void): Promise<void> {
    this.notify = notify;
    if (!canIUse('SystemCapability.Window.SessionManager') || !floatingBall.isFloatingBallEnabled()) {
      throw new Error('当前系统/设备模式不支持闪控球');
    }
    if (this.started) {
      this.notify('系统闪控球已启动');
      return;
    }
    if (this.controller === undefined) {
      this.controller = await floatingBall.create({ context: context });
      this.controller.on('stateChange', (state: floatingBall.FloatingBallState) => {
        this.started = state === floatingBall.FloatingBallState.STARTED;
        this.notify(this.started ? '系统闪控球已启动；请切换应用验证' : '系统闪控球已停止');
      });
      this.controller.on('click', () => {
        this.controller?.restoreMainWindow({
          bundleName: 'com.yisuhua.share', abilityName: 'EntryAbility'
        }).catch((error: BusinessError) => {
          this.notify(`返回上传页失败：${error.code} ${error.message}`);
        });
      });
    }
    // USE_FLOAT_BALL is a permission gate. A manifest entry is not proof of grant.
    await this.controller.startFloatingBall({
      template: floatingBall.FloatingBallTemplate.SIMPLE,
      title: 'Share 上传'
    });
    this.started = true;
    this.notify('系统闪控球已启动；请切换应用验证');
  }

  async stop(): Promise<void> {
    if (this.controller !== undefined && this.started) {
      await this.controller.stopFloatingBall();
      this.started = false;
    }
  }
}

export const systemBall = new SystemBall();
