# ==============================================================================
# Copyright (C) 2026 Adham Cherkaoui Eddeqaqi (0dh4m). All rights reserved.
# Proprietary and confidential. Unauthorized copying or distribution is strictly prohibited.
# Author: Adham Cherkaoui Eddeqaqi (0dh4m) <adamcherkaoui99@gmail.com>
# GitHub: https://github.com/0dh4m
# ==============================================================================

import base64
import hashlib
import os
import re
import time
import urllib.request
from datetime import datetime, timezone

def make_wsse_header(username, password):
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce_raw = os.urandom(16)
    nonce_b64 = base64.b64encode(nonce_raw).decode('utf-8')
    
    sha1 = hashlib.sha1()
    sha1.update(nonce_raw + created.encode('utf-8') + password.encode('utf-8'))
    digest_b64 = base64.b64encode(sha1.digest()).decode('utf-8')
    
    return f"""<s:Header>
    <Security s:mustUnderstand="1" xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <UsernameToken>
        <Username>{username}</Username>
        <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest_b64}</Password>
        <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</Nonce>
        <Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>
      </UsernameToken>
    </Security>
  </s:Header>"""

def _send_soap(ip, username, password, body_content, onvif_port=2020, timeout=4):
    header = make_wsse_header(username, password)
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  {header}
  <s:Body>
    {body_content}
  </s:Body>
</s:Envelope>"""
    url = f"http://{ip}:{onvif_port}/onvif/service"
    req = urllib.request.Request(
        url,
        data=envelope.encode('utf-8'),
        headers={'Content-Type': 'application/soap+xml; charset=utf-8'}
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.status, res.read().decode('utf-8')

def ptz_get_position(ip, username, password, onvif_port=2020):
    try:
        body = '<GetStatus xmlns="http://www.onvif.org/ver20/ptz/wsdl"><ProfileToken>profile_1</ProfileToken></GetStatus>'
        status, xml_res = _send_soap(ip, username, password, body, onvif_port)
        if status == 200:
            m = re.search(r'PanTilt\s+x="([^"]+)"\s+y="([^"]+)"', xml_res)
            if m:
                return float(m.group(1)), float(m.group(2))
    except Exception:
        pass
    return 0.0, 0.0

def ptz_absolute_move(ip, username, password, x, y, onvif_port=2020):
    try:
        body = f"""<AbsoluteMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>profile_1</ProfileToken>
      <Position>
        <PanTilt x="{x:.6f}" y="{y:.6f}" xmlns="http://www.onvif.org/ver10/schema"/>
      </Position>
    </AbsoluteMove>"""
        status, _ = _send_soap(ip, username, password, body, onvif_port)
        return (status == 200), "Absolute move completed" if status == 200 else f"HTTP {status}"
    except Exception as e:
        return False, str(e)

def ptz_move(ip, username, password, direction, step=0.1, onvif_port=2020):
    dx, dy = 0.0, 0.0
    # Adjusted per camera orientation
    if direction == "left":
        dx = abs(float(step))
    elif direction == "right":
        dx = -abs(float(step))
    elif direction == "up":
        dy = abs(float(step))
    elif direction == "down":
        dy = -abs(float(step))
    else:
        return False, "Invalid direction"

    try:
        body = f"""<RelativeMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>profile_1</ProfileToken>
      <Translation>
        <PanTilt x="{dx}" y="{dy}" xmlns="http://www.onvif.org/ver10/schema"/>
      </Translation>
    </RelativeMove>"""
        status, _ = _send_soap(ip, username, password, body, onvif_port)
        return (status == 200), "Move executed" if status == 200 else f"HTTP {status}"
    except Exception as e:
        return False, str(e)

def ptz_privacy_down(ip, username, password, onvif_port=2020):
    """
    Physically tilts camera all the way down into its housing (like the Tapo app).
    Uses AbsoluteMove to y=-1.0 (lowest hardware limit) + RelativeMove downward pulse.
    """
    try:
        x, _ = ptz_get_position(ip, username, password, onvif_port)
        # Drive down to -1.0 (hardware bottom stop)
        ptz_absolute_move(ip, username, password, x, -1.0, onvif_port)
        time.sleep(1.2)
        # Additional relative downward nudge to ensure it's firmly at physical stop
        ptz_move(ip, username, password, "down", 0.5, onvif_port)
        return True, "Lens physically tilted down completely"
    except Exception as e:
        return False, str(e)

def ptz_privacy_up(ip, username, password, onvif_port=2020):
    """
    Restores camera from privacy mode back to comfortable eye-level room view (y=-0.35).
    """
    try:
        x, _ = ptz_get_position(ip, username, password, onvif_port)
        ptz_absolute_move(ip, username, password, x, -0.35, onvif_port)
        return True, "Lens returned to normal viewing angle"
    except Exception as e:
        return False, str(e)
