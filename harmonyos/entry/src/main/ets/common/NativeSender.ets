import { common } from '@kit.AbilityKit';
import { fileIo as fs, fileUri } from '@kit.CoreFileKit';
import { cryptoFramework } from '@kit.CryptoArchitectureKit';
import { http } from '@kit.NetworkKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { receiverUrl, checkInfo, checkReceipt, Receipt, ServerInfo } from './Protocol';

export interface SendResult {
  receipt: Receipt;
  cleanupWarning: string;
}

function tokenHeader(token: string): string {
  if (token.length === 0 || token.length > 128 || /[\r\n]/.test(token)) {
    throw new Error('请输入电脑面板中的配对密码');
  }
  return `Bearer ${token}`;
}

export class NativeSender {
  private current: http.HttpRequest | undefined = undefined;
  private sending: boolean = false;

  async info(address: string, token: string): Promise<ServerInfo> {
    const base = receiverUrl(address);
    const authorization = tokenHeader(token);
    const task = http.createHttp();
    try {
      const result = await task.request(`${base}/v1/info`, {
        method: http.RequestMethod.GET,
        header: { 'Authorization': authorization },
        expectDataType: http.HttpDataType.STRING,
        usingCache: false,
        usingProxy: false,
        connectTimeout: 6000,
        readTimeout: 10000
      });
      return checkInfo(result.responseCode, result.result as string);
    } finally {
      task.destroy();
    }
  }

  async send(context: common.UIAbilityContext, uri: string, address: string, token: string,
    maxBytes: number, progress: (message: string) => void): Promise<SendResult> {
    if (this.sending) {
      throw new Error('已有文件正在发送');
    }
    const base = receiverUrl(address);
    const authorization = tokenHeader(token);
    if (!uri.startsWith('file://')) {
      throw new Error('仅支持已授权的本地文件 URI');
    }
    const name = new fileUri.FileUri(uri).name;
    this.sending = true;
    let directory = '';
    let payload = '';
    let source: fs.File | undefined = undefined;
    let cached: fs.File | undefined = undefined;
    let receipt: Receipt | undefined = undefined;
    let cleanupWarning = '';
    let failure: Error | undefined = undefined;
    try {
      source = await fs.open(uri, fs.OpenMode.READ_ONLY);
      const stat = await fs.stat(source.fd);
      if (!stat.isFile() || stat.size > maxBytes) {
        throw new Error(`不是普通文件，或超过电脑限制 ${maxBytes} 字节`);
      }
      directory = await fs.mkdtemp(`${context.cacheDir}/share-XXXXXX`);
      payload = `${directory}/payload`;
      progress('正在准备原始文件…');
      await fs.copyFile(source.fd, payload);
      await fs.close(source);
      source = undefined;
      cached = await fs.open(payload, fs.OpenMode.READ_ONLY);
      const cachedStat = await fs.stat(cached.fd);
      if (cachedStat.size !== stat.size) {
        throw new Error('准备文件时源文件发生变化，请重新选择');
      }
      const md = cryptoFramework.createMd('SHA256');
      const buffer = new ArrayBuffer(256 * 1024);
      let offset = 0;
      while (offset < stat.size) {
        const count = await fs.read(cached.fd, buffer, {
          offset: offset, length: Math.min(buffer.byteLength, stat.size - offset)
        });
        if (count <= 0) {
          throw new Error('文件读取不完整');
        }
        await md.update({ data: new Uint8Array(buffer, 0, count) });
        offset += count;
        progress(`校验中 ${Math.floor(offset * 100 / stat.size)}%`);
      }
      const digest = await md.digest();
      let sha = '';
      for (let i = 0; i < digest.data.length; i++) {
        sha += digest.data[i].toString(16).padStart(2, '0');
      }
      await fs.close(cached);
      cached = undefined;
      const task = http.createHttp();
      this.current = task;
      task.on('dataSendProgress', (event: http.DataSendProgressInfo) => {
        if (event.sendSize > 0) {
          progress('正在发送文件，等待电脑校验保存…');
        }
      });
      // Do not set remoteFileName: native filePath mode can stream the cached file.
      // The original filename is carried separately in the authenticated query.
      const response = await task.request(`${base}/v1/form-files?name=${encodeURIComponent(name)}`, {
        method: http.RequestMethod.POST,
        header: {
          'Authorization': authorization,
          'Content-Type': 'multipart/form-data',
          'X-File-Size': String(stat.size),
          'X-Content-SHA256': sha
        },
        multiFormDataList: [{ name: 'file', contentType: 'application/octet-stream', filePath: payload }],
        expectDataType: http.HttpDataType.STRING,
        usingProtocol: http.HttpProtocol.HTTP1_1,
        usingCache: false,
        usingProxy: false,
        connectTimeout: 6000,
        readTimeout: 3600000
      });
      receipt = checkReceipt(response.responseCode, response.result as string, stat.size, sha);
    } catch (error) {
      failure = error as Error;
    } finally {
      this.current?.destroy();
      this.current = undefined;
      // Attempt all cleanup actions; expose any residual cache warning to the UI.
      if (source !== undefined) {
        try { await fs.close(source); } catch (error) { cleanupWarning = `源文件关闭失败 ${(error as BusinessError).code}`; }
      }
      if (cached !== undefined) {
        try { await fs.close(cached); } catch (error) { cleanupWarning += ` 缓存文件关闭失败 ${(error as BusinessError).code}`; }
      }
      if (payload.length > 0) {
        try { await fs.unlink(payload); } catch (error) {
          if ((error as BusinessError).code !== 13900002) {
            cleanupWarning += ` 缓存清理失败 ${(error as BusinessError).code}`;
          }
        }
      }
      if (directory.length > 0) {
        try { await fs.rmdir(directory); } catch (error) { cleanupWarning += ` 缓存目录清理失败 ${(error as BusinessError).code}`; }
      }
      this.sending = false;
    }
    if (failure !== undefined) {
      if (cleanupWarning.length > 0) {
        const code = (failure as BusinessError).code;
        throw new Error(`${code ? String(code) + '：' : ''}${failure.message}；${cleanupWarning}`);
      }
      throw failure;
    }
    if (receipt === undefined) {
      throw new Error('未取得保存回执');
    }
    return { receipt: receipt, cleanupWarning: cleanupWarning };
  }
}
