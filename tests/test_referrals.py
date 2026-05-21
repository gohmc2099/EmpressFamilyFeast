import importlib
import os
import tempfile
import unittest


class ReferralAppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_PATH"] = os.path.join(cls.temp_dir.name, "empress-test.db")
        os.environ["GOOGLE_SHEET_ID"] = ""
        os.environ["FLASK_SECRET_KEY"] = "test-secret"

        app_module = importlib.import_module("dashboard.app")
        cls.app = app_module.app
        cls.app.config["TESTING"] = True
        cls.db = importlib.import_module("db").get_db()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.temp_dir.cleanup()

    def test_public_referral_submission_persists(self):
        response = self.app.test_client().post("/refer", data={
            "referrer_name": "Aisha Brown",
            "referrer_phone": "+44 7700 900001",
            "referrer_email": "aisha@example.com",
            "family_name": "Mensah family",
            "contact_name": "Ama Mensah",
            "contact_phone": "+44 7700 900002",
            "contact_email": "ama@example.com",
            "address": "10 King Street",
            "postcode": "N1 1AA",
            "household_size": "4",
            "preferred_contact": "whatsapp",
            "dietary_needs": "No peanuts",
            "reason": "Needs short-term meal support",
            "consent": "on",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Referral received", response.data)
        referrals = self.db.get_all_referrals()
        referral = next(r for r in referrals if r["family_name"] == "Mensah family")
        self.assertEqual(referral["status"], "new")
        self.assertEqual(referral["household_size"], 4)
        self.assertTrue(referral["consent"])

    def test_referral_status_can_be_updated(self):
        created_at = "2026-05-21 04:20:00"
        self.db.add_referral(
            referral_id="REF-TEST-0001",
            referrer_name="Case Worker",
            referrer_phone="+44 7700 900003",
            referrer_email="worker@example.com",
            family_name="Okafor family",
            contact_name="Chidi Okafor",
            contact_phone="+44 7700 900004",
            contact_email="",
            address="25 Queen Road",
            postcode="E8 2BB",
            household_size=3,
            preferred_contact="phone",
            dietary_needs="Halal",
            reason="New baby at home",
            consent=True,
            created_at=created_at,
        )

        response = self.app.test_client().post(
            "/referrals/REF-TEST-0001",
            data={"status": "eligible", "notes": "Confirmed by phone."},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        referral = self.db.get_referral("REF-TEST-0001")
        self.assertEqual(referral["status"], "eligible")
        self.assertEqual(referral["notes"], "Confirmed by phone.")


if __name__ == "__main__":
    unittest.main()
