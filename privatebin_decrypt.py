# -*- coding: utf-8 -*-
"""PrivateBin 解密工具 (最终版).

该模块用于解密 PrivateBin (paste.to) 的加密内容。

使用方法:
    from privatebin_decrypt import PrivateBinDecryptor

    # 方式1: 使用完整 URL
    decryptor = PrivateBinDecryptor()
    result = decryptor.decrypt_from_url(
        'https://paste.to/?e51ef1ae8a2d7c9b#FPgZrmNMsdhq8wm2',
        password='5253'
    )

    # 方式2: 分步操作
    decryptor = PrivateBinDecryptor()
    decryptor.fetch_data('paste_id')
    result = decryptor.decrypt('key', password='')
"""

import base64
import hashlib
import json
import zlib
from typing import Dict, Tuple
from urllib.parse import urlparse, parse_qs

import requests
import base58


class PrivateBinDecryptor:
    """PrivateBin 解密器类.

    该类实现了与 PrivateBin JavaScript 代码完全一致的解密逻辑:
    1. 从 URL hash 提取 base58 编码的密钥
    2. Base58 解码并 pad 到 32 字节
    3. 从服务器获取加密数据
    4. 如果有密码，拼接密钥和密码
    5. 使用 PBKDF2 派生 AES 密钥
    6. 使用 AES-GCM 解密 (使用 adata 作为 AAD)
    7. 使用 zlib 解压缩
    """

    def __init__(self, base_url: str = 'https://paste.to'):
        """初始化解密器.

        Args:
            base_url: PrivateBin 服务的基础 URL
        """
        self.base_url = base_url.rstrip('/')
        self.paste_data: Dict = None

    def extract_key_from_url(self, url: str) -> Tuple[str, str]:
        """从完整 URL 中提取 paste_id 和解密密钥.

        该方法解析 PrivateBin URL，提取 paste_id 和 hash 部分的密钥。

        Args:
            url: 完整的 PrivateBin URL
                 例如: https://paste.to/?e51ef1ae8a2d7c9b#FPgZrmNMsdhq8wm2DQkHE2u8FgHLkpZtwLi8a8Ky7xjL

        Returns:
            (paste_id, key) 元组
        """
        parsed = urlparse(url)

        # 从查询参数提取 paste_id
        query_params = parse_qs(parsed.query)
        if 'pasteid' in query_params:
            paste_id = query_params['pasteid'][0]
        else:
            paste_id = parsed.query.lstrip('?')

        # 从 hash 提取密钥
        key = parsed.fragment
        if key.startswith('-'):
            key = key[1:]

        # 移除额外的查询参数
        if '&' in key:
            key = key.split('&')[0]

        return paste_id, key

    def fetch_data(self, paste_id: str) -> Dict:
        """从服务器获取加密的粘贴数据.

        该方法向 PrivateBin 服务器发送请求，获取指定 paste_id 的加密数据。

        Args:
            paste_id: 粘贴的唯一标识符 (16位字符)

        Returns:
            包含加密数据的字典
        """
        url = f'{self.base_url}/?pasteid={paste_id}'

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        self.paste_data = response.json()
        return self.paste_data

    def decrypt(self, key: str, password: str = '') -> str:
        """解密粘贴内容.

        该方法执行完整的解密流程。

        Args:
            key: Base58 编码的密钥 (从 URL hash 提取)
            password: 可选的密码

        Returns:
            解密后的明文内容
        """
        if not self.paste_data:
            raise ValueError('请先调用 fetch_data 获取数据')

        # ===============================
        # 步骤 1: Base58 解码密钥并 pad 到 32 字节
        # ===============================
        key_bytes = base58.b58decode(key)
        # 模拟 JS: .padStart(32, '\u0000')
        key_bytes = key_bytes.rjust(32, b'\x00')

        # ===============================
        # 步骤 2: 处理密码
        # ===============================
        if password:
            # 模拟 JS 的 stringToArraybuffer(password):
            # 把密码的每个字符的 charCodeAt 转成字节
            password_bytes = bytes(ord(c) for c in password)
            key_bytes += password_bytes

        # ===============================
        # 步骤 3: 获取加密参数
        # ===============================
        ct = self.paste_data['ct']
        adata = self.paste_data['adata']
        spec = adata[0]

        # ===============================
        # 步骤 4: PBKDF2 派生 AES 密钥
        # ===============================
        salt = base64.b64decode(spec[1])
        iterations = spec[2]

        derived_key = hashlib.pbkdf2_hmac(
            'sha256',
            key_bytes,
            salt,
            iterations,
            dklen=32
        )

        # ===============================
        # 步骤 5: 构建 AAD
        # ===============================
        # 必须与 JS 的 JSON.stringify(adata) 完全一致！
        adata_str = json.dumps(adata, separators=(',', ':'))
        aad = adata_str.encode('utf-8')

        # ===============================
        # 步骤 6: AES-GCM 解密
        # ===============================
        iv = base64.b64decode(spec[0])
        ciphertext_bytes = base64.b64decode(ct)

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(derived_key)
        plaintext = aesgcm.decrypt(iv, ciphertext_bytes, aad)

        # ===============================
        # 步骤 7: zlib 解压缩
        # ===============================
        compression = spec[7] if len(spec) > 7 else 'none'
        if compression == 'zlib':
            plaintext = zlib.decompress(plaintext, -zlib.MAX_WBITS)

        return plaintext.decode('utf-8')

    def decrypt_from_url(self, url: str, password: str = '') -> str:
        """从完整 URL 解密粘贴内容.

        这是最便捷的方法，一行代码完成所有操作。

        Args:
            url: 完整的 PrivateBin URL
            password: 可选的密码

        Returns:
            解密后的明文内容
        """
        paste_id, key = self.extract_key_from_url(url)
        self.fetch_data(paste_id)
        return self.decrypt(key, password)


def decrypt_privatebin(url: str, password: str = '') -> str:
    """快速解密 PrivateBin 链接.

    这是最简化的接口，一行代码完成解密。

    Args:
        url: 完整的 PrivateBin URL
        password: 可选的密码

    Returns:
        解密后的明文内容
    """
    decryptor = PrivateBinDecryptor()
    return decryptor.decrypt_from_url(url, password)


if __name__ == '__main__':
    # 命令行使用
    import sys

    if len(sys.argv) < 2:
        print('用法: python privatebin_decrypt.py <url> [password]')
        print('示例: python privatebin_decrypt.py "https://paste.to/?xxx#key" 5253')
        sys.exit(1)

    url = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else ''

    try:
        result = decrypt_privatebin(url, password)
        print('解密成功:')
        print('=' * 80)
        print(result)
    except Exception as e:
        print(f'解密失败: {e}')
        import traceback
        traceback.print_exc()
