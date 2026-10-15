import { common } from '@kit.AbilityKit';
import { picker } from '@kit.CoreFileKit';
import { photoAccessHelper } from '@kit.MediaLibraryKit';
import { preferences } from '@kit.ArkData';
import { BusinessError } from '@kit.BasicServicesKit';
import { NativeSender } from '../common/NativeSender';
import { systemBall } from '../common/SystemBall';
import { localFileUris } from '../common/DropFiles';
import { checkStoreUpdate } from '../common/StoreUpdates';
import { receiverUrl } from '../common/Protocol';

interface Connection {
  address: string;
  password: string;
}

@Entry
@Component
struct Index {
  @State address: string = '';
  @State password: string = '';
  @State status: string = '填写电脑地址和配对密码后连接';
  @State ballStatus: string = '未启动';
  @State busy: boolean = false;
  @State loading: boolean = true;
  @State ballBusy: boolean = false;
  @State updateBusy: boolean = false;
  @State updateStatus: string = '版本 0.1.0 · 开发版本';
  @State history: string[] = [];
  private store: preferences.Preferences | undefined = undefined;
  private sender: NativeSender = new NativeSender();

  aboutToAppear(): void {
    this.loadConnection();
  }

  private context(): common.UIAbilityContext {
    return this.getUIContext().getHostContext() as common.UIAbilityContext;
  }

  private errorText(error: BusinessError): string {
    return error.code ? `${error.code}：${error.message}` : error.message;
  }

  private async loadConnection(): Promise<void> {
    try {
      this.store = await preferences.getPreferences(this.context(), { name: 'share_connection' });
      const address = await this.store.get('address', '') as string;
      const password = await this.store.get('password', '') as string;
      this.address = address;
      this.password = password;
    } catch (error) {
      this.status = `读取连接配置失败：${this.errorText(error as BusinessError)}`;
    } finally {
      this.loading = false;
    }
  }

  private snapshot(): Connection {
    return { address: receiverUrl(this.address), password: this.password };
  }

  private async saveConnection(connection: Connection): Promise<void> {
    if (this.store === undefined) {
      this.store = await preferences.getPreferences(this.context(), { name: 'share_connection' });
    }
    await this.store.put('address', connection.address);
    await this.store.put('password', connection.password);
    await this.store.flush();
  }

  private async connect(): Promise<void> {
    if (this.busy || this.loading) { return; }
    this.busy = true;
    try {
      const connection = this.snapshot();
      const info = await this.sender.info(connection.address, connection.password);
      await this.saveConnection(connection);
      this.status = `电脑已连接 · 单文件限制 ${Math.floor(info.max_bytes / 1024 / 1024)} MiB`;
    } catch (error) {
      this.status = this.errorText(error as BusinessError);
    } finally {
      this.busy = false;
    }
  }

  private async sendUris(uris: string[], connection: Connection): Promise<void> {
    if (uris.length === 0) {
      this.status = '已取消选择';
      return;
    }
    const info = await this.sender.info(connection.address, connection.password);
    await this.saveConnection(connection);
    let saved = 0;
    for (let i = 0; i < uris.length; i++) {
      try {
        const result = await this.sender.send(this.context(), uris[i], connection.address, connection.password,
          info.max_bytes, (message: string) => { this.status = `${i + 1}/${uris.length} · ${message}`; });
        saved++;
        const record = `${result.receipt.name} · ${result.receipt.bytes} 字节 · 电脑已校验保存`;
        this.history = [record, ...this.history].slice(0, 100);
        if (result.cleanupWarning.length > 0) {
          this.status = `已保存 ${saved}/${uris.length}；${result.cleanupWarning}，已停止后续文件`;
          return;
        }
      } catch (error) {
        this.status = `已保存 ${saved}/${uris.length}；${this.errorText(error as BusinessError)}。已停止后续文件，请先核对电脑`;
        return;
      }
    }
    this.status = `${saved} 个文件已由电脑校验保存`;
  }

  private async chooseFiles(images: boolean): Promise<void> {
    if (this.busy || this.loading) { return; }
    this.busy = true;
    try {
      const connection = this.snapshot();
      let uris: string[] = [];
      if (images) {
        const options = new photoAccessHelper.PhotoSelectOptions();
        options.MIMEType = photoAccessHelper.PhotoViewMIMETypes.IMAGE_TYPE;
        options.maxSelectNumber = 20;
        const photoPicker = new photoAccessHelper.PhotoViewPicker();
        uris = (await photoPicker.select(options)).photoUris;
      } else {
        const filePicker = new picker.DocumentViewPicker(this.context());
        uris = await filePicker.select({ maxSelectNumber: 20 });
      }
      await this.sendUris(uris, connection);
    } catch (error) {
      this.status = `选择或发送失败：${this.errorText(error as BusinessError)}`;
    } finally {
      this.busy = false;
    }
  }

  private async receiveDrop(event: DragEvent): Promise<void> {
    if (this.busy || this.loading) {
      event.setResult(DragResult.DRAG_FAILED);
      return;
    }
    this.busy = true;
    try {
      const connection = this.snapshot();
      const uris = localFileUris(event.getData());
      event.setResult(DragResult.DRAG_SUCCESSFUL);
      await this.sendUris(uris, connection);
    } catch (error) {
      event.setResult(DragResult.DRAG_FAILED);
      this.status = `拖入失败：${this.errorText(error as BusinessError)}`;
    } finally {
      this.busy = false;
    }
  }

  private async startBall(): Promise<void> {
    this.ballBusy = true;
    try {
      await systemBall.start(this.context(), (message: string) => { this.ballStatus = message; });
    } catch (error) {
      this.ballStatus = `启动失败：${this.errorText(error as BusinessError)}`;
    } finally {
      this.ballBusy = false;
    }
  }

  private async stopBall(): Promise<void> {
    this.ballBusy = true;
    try {
      await systemBall.stop();
      this.ballStatus = '已停止';
    } catch (error) {
      this.ballStatus = `停止失败：${this.errorText(error as BusinessError)}`;
    } finally {
      this.ballBusy = false;
    }
  }

  private async checkUpdate(): Promise<void> {
    if (this.updateBusy || this.busy) { return; }
    this.updateBusy = true;
    try {
      this.updateStatus = await checkStoreUpdate(this.context());
    } catch (error) {
      this.updateStatus = `检查更新失败：${this.errorText(error as BusinessError)}`;
    } finally {
      this.updateBusy = false;
    }
  }

  build() {
    Scroll() {
      Column({ space: 16 }) {
        Text('Share').fontSize(36).fontWeight(FontWeight.Bold).width('100%')
        Text('将图片和文件送到电脑默认文件夹').fontColor('#566174').width('100%')
        TextInput({ text: this.address, placeholder: '电脑地址，例如 192.168.1.9:8765' })
          .enabled(!this.busy && !this.loading).onChange((value: string) => { this.address = value; })
        TextInput({ text: this.password, placeholder: '电脑面板中的配对密码' })
          .type(InputType.Password).enabled(!this.busy && !this.loading).onChange((value: string) => { this.password = value; })
        Button('连接电脑并保存设置').width('100%').enabled(!this.busy && !this.loading).onClick(() => { this.connect(); })
        Row({ space: 12 }) {
          Button('选择图片').layoutWeight(1).enabled(!this.busy && !this.loading).onClick(() => { this.chooseFiles(true); })
          Button('选择文件').layoutWeight(1).enabled(!this.busy && !this.loading).onClick(() => { this.chooseFiles(false); })
        }.width('100%')
        Column({ space: 8 }) {
          Text('拖入图片或文件到这里').fontSize(20).fontWeight(FontWeight.Medium)
          Text('上传页打开时可用；来源应用需提供文件数据').fontSize(13).fontColor('#566174')
        }.width('100%').height(130).backgroundColor('#eef3ff').borderRadius(18)
          .justifyContent(FlexAlign.Center).onDrop((event: DragEvent) => { this.receiveDrop(event); })
        Text(this.status).width('100%').fontColor('#2459e0')
        Text('传输时请保持上传页前台；进度完成后仍需等待电脑保存回执。').fontSize(13).width('100%').fontColor('#566174')
        Divider()
        Row({ space: 12 }) {
          Button('开启系统闪控球').layoutWeight(1).enabled(!this.ballBusy).onClick(() => { this.startBall(); })
          Button('关闭球').enabled(!this.ballBusy).onClick(() => { this.stopBall(); })
        }.width('100%')
        Text(this.ballStatus).width('100%')
        Text('点击系统球返回上传页。当前尚未验证直接把文件拖到系统球上的能力。')
          .fontSize(13).fontColor('#566174').width('100%')
        Divider()
        Button('检查应用更新').enabled(!this.updateBusy && !this.busy)
          .onClick(() => { this.checkUpdate(); })
        Text(this.updateStatus).fontSize(13).fontColor('#566174').width('100%')
        Divider()
        Text('最近发送').fontSize(20).fontWeight(FontWeight.Bold).width('100%')
        ForEach(this.history, (line: string) => {
          Text(line).width('100%').padding(10).backgroundColor('#f5f7fb').borderRadius(8)
        })
      }.padding(24).width('100%').alignItems(HorizontalAlign.Start)
    }.width('100%').height('100%')
  }
}
