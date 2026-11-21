# ==============================================================================
# Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
# Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
# Author: Adham Cherkaoui Eddeqaqi (0dh4m) <adamcherkaoui99@gmail.com>
# GitHub: https://github.com/0dh4m
# ==============================================================================

import urllib.request
import ptz

url = 'http://192.168.1.30:2020/onvif/service'
header = ptz.make_wsse_header("adhamch", "adamfarA1")
body = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  {header}
  <s:Body>
    <RelativeMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>profile_1</ProfileToken>
      <Translation>
        <PanTilt x="0.0" y="-0.3" xmlns="http://www.onvif.org/ver10/schema"/>
      </Translation>
    </RelativeMove>
  </s:Body>
</s:Envelope>"""

req = urllib.request.Request(
    url,
    data=body.encode('utf-8'),
    headers={'Content-Type': 'application/soap+xml; charset=utf-8'}
)

try:
    with urllib.request.urlopen(req, timeout=3) as res:
        print('Status:', res.status, res.read().decode())
except urllib.error.HTTPError as e:
    print('HTTPError code:', e.code)
    print('Error Body:', e.read().decode())
except Exception as ex:
    print('Ex:', ex)
