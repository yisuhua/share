// Platform-independent contract checks. Node tests do not validate HarmonyOS APIs.
export interface ServerInfo {
  protocol: number;
  max_bytes: number;
  form_upload: boolean;
}

export interface Receipt {
  name: string;
  bytes: number;
  sha256: string;
}

export function receiverUrl(input: string): string {
  const match = /^(?:http:\/\/)?(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d{1,5})\/?$/.exec(input.trim());
  if (match === null) {
    throw new Error('请输入电脑局域网 IPv4 地址和端口，例如 192.168.1.9:8765');
  }
  const octets = [Number(match[1]), Number(match[2]), Number(match[3]), Number(match[4])];
  const port = Number(match[5]);
  if (octets.some((value: number) => value > 255) || port < 1 || port > 65535) {
    throw new Error('IP 地址或端口无效');
  }
  const local = octets[0] === 10 || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
    || (octets[0] === 192 && octets[1] === 168);
  if (!local) {
    throw new Error('仅支持可信局域网中的私有 IPv4 地址');
  }
  return `http://${octets.join('.')}:${port}`;
}

export function checkInfo(status: number, body: string): ServerInfo {
  if (status !== 200) {
    throw new Error(`连接失败，HTTP ${status}；请检查配对密码和电脑服务`);
  }
  const value = JSON.parse(body) as ServerInfo;
  if (value === null || typeof value !== 'object' || value.protocol !== 1
    || value.form_upload !== true || !Number.isSafeInteger(value.max_bytes) || value.max_bytes <= 0) {
    throw new Error('电脑接收器版本不兼容，请更新到支持原生文件上传的版本');
  }
  return value;
}

export function checkReceipt(status: number, body: string, size: number, sha: string): Receipt {
  if (status !== 201) {
    throw new Error(`接收失败，HTTP ${status}；未取得有效保存回执`);
  }
  const value = JSON.parse(body) as Receipt;
  if (value === null || typeof value !== 'object' || typeof value.name !== 'string'
    || value.name.length === 0 || value.bytes !== size || value.sha256 !== sha) {
    throw new Error('保存回执不匹配；请在电脑核对文件，勿盲目重复上传');
  }
  return value;
}
