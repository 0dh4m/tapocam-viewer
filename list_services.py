# ==============================================================================
# Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
# Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
# Author: Adham Cherkaoui Eddeqaqi (0dh4m) <adamcherkaoui99@gmail.com>
# GitHub: https://github.com/0dh4m
# ==============================================================================

import urllib.request
import re

body = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body>
    <GetServices xmlns="http://www.onvif.org/ver10/device/wsdl">
      <IncludeCapability>false</IncludeCapability>
    </GetServices>
  </s:Body>
</s:Envelope>"""

req = urllib.request.Request(
    'http://192.168.1.30:2020/onvif/device_service',
    data=body.encode(),
    headers={'Content-Type': 'application/soap+xml'}
)
resp = urllib.request.urlopen(req).read().decode()
for match in re.finditer(r'<tds:Namespace>(.*?)</tds:Namespace>\s*<tds:XAddr>(.*?)</tds:XAddr>', resp):
    print(match.group(1), '-->', match.group(2))
