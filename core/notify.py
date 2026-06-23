"""
ศูนย์แจ้งเตือน — channel-agnostic
สร้าง Notification ลง DB เสมอ (แสดงในระบบ) และพยายาม push ภายนอกถ้าตั้งค่าไว้

หมายเหตุ 2027: LINE Notify ถูกปิดบริการแล้ว (มี.ค. 2025)
ระบบนี้รองรับ push ผ่าน LINE Messaging API หรือ webchat อื่น ๆ ได้แบบ pluggable
โดยไม่ทำให้การทำงานหลักพัง ถ้ายังไม่ได้ตั้งค่า
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def notify(tenant, title, message='', level='info', category='system', link=''):
    """สร้างการแจ้งเตือน 1 รายการ — คืน Notification object"""
    from .models import Notification

    n = Notification.objects.create(
        tenant=tenant,
        title=title,
        message=message,
        level=level,
        category=category,
        link=link,
    )
    _push_external(tenant, title, message, level)
    return n


def _push_external(tenant, title, message, level):
    """พยายามส่ง push ภายนอก — เงียบถ้าไม่ได้ตั้งค่า (ไม่ทำให้ระบบหลักพัง)"""
    token = getattr(settings, 'LINE_CHANNEL_ACCESS_TOKEN', '')
    to = getattr(settings, 'LINE_NOTIFY_TO', '')
    if not token or not to:
        return
    try:
        import requests

        requests.post(
            'https://api.line.me/v2/bot/message/push',
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json={
                'to': to,
                'messages': [{'type': 'text', 'text': f"[{level.upper()}] {title}\n{message}".strip()}],
            },
            timeout=5,
        )
    except Exception as exc:  # noqa: BLE001 — แจ้งเตือนล้มเหลวต้องไม่ล้มงานหลัก
        logger.warning('External push failed: %s', exc)


def audit(action, user=None, tenant=None, model_name='', object_id='', summary=''):
    """บันทึก AuditLog 1 รายการ"""
    from .models import AuditLog

    return AuditLog.objects.create(
        tenant=tenant,
        user=user if (user and getattr(user, 'is_authenticated', False)) else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        summary=summary,
    )
