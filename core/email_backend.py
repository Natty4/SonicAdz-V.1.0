import asyncio
import logging
import httpx
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        success = False
        loop = asyncio.new_event_loop() 
        asyncio.set_event_loop(loop) 
        tasks = [self._send_email(message) for message in email_messages]

        try:
            
            success = loop.run_until_complete(asyncio.gather(*tasks))
        except Exception as e:
            logger.error(f"Error running async tasks for emails: {str(e)}")
        finally:
            loop.close()  

        return success

    async def _send_email(self, message):
        to_email = message.to[0]
        subject = message.subject
        text_content = message.body 
        html_content = None
        if message.alternatives:
            for content, mimetype in message.alternatives:
                if mimetype == 'text/html':
                    html_content = content
                    break

        if not html_content:
            html_content = message.body 

        to_name = message.to[0]

        success = await self.send_confirmation_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content, 
            to_name=to_name,
        )

        if not success:
            logger.error(f"Failed to send confirmation email to {to_email}")

    async def send_confirmation_email(
        self, to_email: str, subject: str, html_content: str, text_content: str = None, to_name: str = "User"
    ) -> bool:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "Content-Type": "application/json",
            "api-key": settings.SENDINBLUE_API_KEY,
        }

        payload = {
            "sender": {
                "name": settings.FROM_NAME,
                "email": settings.FROM_EMAIL
            },
            "to": [{
                "email": to_email,
                "name": to_name,
            }],
            "subject": subject,
            "htmlContent": html_content,
        }

        if text_content:
            payload["textContent"] = text_content

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
                resp.raise_for_status() 
                if resp.status_code in (200, 201, 202):
                    return True
                else:
                    logger.error(f"Failed to send email via Brevo API: {resp} : {resp.text}")
                    print(f"Failed to send email via Brevo API: {resp} : {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending email via Brevo API: {str(e)}")
            return False
