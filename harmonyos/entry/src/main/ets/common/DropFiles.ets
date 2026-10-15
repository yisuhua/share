import { unifiedDataChannel, uniformDataStruct, uniformTypeDescriptor } from '@kit.ArkData';

// This adapter is for the upload PAGE only. It is not a system-ball drop handler.
export function localFileUris(data: unifiedDataChannel.UnifiedData): string[] {
  const uris: string[] = [];
  const records = data.getRecords();
  for (let i = 0; i < records.length; i++) {
    const record = records[i];
    let uri = '';
    if (record.getTypes().includes(uniformTypeDescriptor.UniformDataType.FILE_URI)) {
      uri = (record.getEntry(uniformTypeDescriptor.UniformDataType.FILE_URI) as uniformDataStruct.FileUri).oriUri;
    } else if (record.getType() === uniformTypeDescriptor.UniformDataType.IMAGE) {
      uri = (record as unifiedDataChannel.Image).imageUri;
    } else if (record.getType() === uniformTypeDescriptor.UniformDataType.FILE) {
      uri = (record as unifiedDataChannel.File).uri;
    }
    if (typeof uri !== 'string' || !uri.startsWith('file://')) {
      throw new Error('拖入内容没有可读取的本地文件，请使用图片或文件选择按钮');
    }
    if (!uris.includes(uri)) {
      uris.push(uri);
    }
  }
  if (uris.length === 0) {
    throw new Error('未取得拖入文件；来源应用可能没有开放文件数据');
  }
  return uris;
}
