# ==============================================================================
# Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
# Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
# Author: Adham Cherkaoui Eddeqaqi (0dh4m) <adamcherkaoui99@gmail.com>
# GitHub: https://github.com/0dh4m
# ==============================================================================

import urllib.request
import re
from datetime import datetime, timezone

body = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body><GetSystemDateAndTime xmlns="http://www.onvif.org/ver10/device/wsdl"/></s:Body>
</s:Envelope>"""

req = urllib.request.Request(
    'http://192.168.1.30:2020/onvif/device_service',
    data=body.encode(),
    headers={'Content-Type': 'application/soap+xml'}
)
resp = urllib.request.urlopen(req).read().decode()
h = int(re.search(r'<tt:Hour>(\d+)', resp).group(1))
m = int(re.search(r'<tt:Minute>(\d+)', resp).group(1))
s = int(re.search(r'<tt:Second>(\d+)', resp).group(1))
cam_sec = h * 3600 + m * 60 + s

now = datetime.now(timezone.utc)
loc_sec = now.hour * 3600 + now.minute * 60 + now.second
print(f"Camera UTC: {h:02d}:{m:02d}:{s:02d}")
print(f"Local  UTC: {now.hour:02d}:{now.minute:02d}:{now.second:02d}")
print(f"Time difference (Local - Camera): {loc_sec - cam_sec} seconds")
