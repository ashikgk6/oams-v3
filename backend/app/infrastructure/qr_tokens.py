from app.services import qr as qr_impl


class HmacQrTokenService:
    def sign(self, kiosk_id: int, kiosk_secret: str) -> tuple[str, int]:
        return qr_impl.sign_qr_payload(kiosk_id, kiosk_secret)

    def verify(self, token: str, lookup_secret) -> dict:
        return qr_impl.verify_qr_token(token, lookup_secret)
