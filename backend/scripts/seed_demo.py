"""Seed Script for HealthTech Platform Demo (Week 6 Final Capstone).

Provisions:
1. Default Administrator (`admin@healthtech.test` / `AdminPass123!`)
2. Default Member (`member@healthtech.test` / `MemberPass123!`)
3. Full Member Profile (Demographics, Wellness, Emergency Contact)
4. Recomputes Profile Completion Status
5. Initializes RAG Document Store with Clinic Policies
6. Initializes Background Task Queue with a baseline indexing job
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add current directory and parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Role
from profiles.models import CompletionStatus, HealthProfile, Demographics, WellnessPreferences, EmergencyContact
from rag.advanced_engine import get_advanced_store
from agents.task_queue import get_task_queue

User = get_user_model()


def seed_database():
    print("[1/5] Seeding Users...")
    # Admin User
    admin, created = User.objects.get_or_create(
        email="admin@healthtech.test",
        defaults={"role": Role.ADMIN, "is_active": True},
    )
    if created:
        admin.set_password("AdminPass123!")
        admin.save()
        print("  -> Created Admin: admin@healthtech.test (Password: AdminPass123!)")
    else:
        print("  -> Admin exists: admin@healthtech.test")

    # Member User
    member, created = User.objects.get_or_create(
        email="member@healthtech.test",
        defaults={"role": Role.USER, "is_active": True},
    )
    if created:
        member.set_password("MemberPass123!")
        member.save()
        print("  -> Created Member: member@healthtech.test (Password: MemberPass123!)")
    else:
        print("  -> Member exists: member@healthtech.test")

    print("[2/5] Seeding Member Health Profile...")
    profile, _ = HealthProfile.objects.get_or_create(user=member)

    Demographics.objects.update_or_create(
        profile=profile,
        defaults={
            "date_of_birth": "1990-05-15",
            "gender": "FEMALE",
            "blood_group": "O+",
            "country": "US",
            "preferred_language": "English",
        },
    )

    WellnessPreferences.objects.update_or_create(
        profile=profile,
        defaults={
            "activity_level": "MODERATE",
            "diet_preference": "NO_PREFERENCE",
            "sleep_goal_hours": 8.0,
            "reminder_channel": "EMAIL",
            "contact_preference": "EMAIL",
            "wellness_goals": "Maintain good cardiovascular health and regular exercise",
        },
    )

    EmergencyContact.objects.update_or_create(
        profile=profile,
        relationship="SPOUSE",
        defaults={
            "name": "John Doe",
            "phone": "+15559876543",
            "is_primary": True,
        },
    )
    profile.completion_percent = 100
    profile.completion_status = CompletionStatus.COMPLETE
    profile.save()
    print(f"  -> Completed Member profile: {profile.completion_status} ({profile.completion_percent}%)")

    print("[3/5] Verifying RAG Document Store...")
    store = get_advanced_store()
    print(f"  -> RAG Store active: {len(store.documents)} policies indexed across {len(store.chunks)} chunks")

    print("[4/5] Initializing Task Queue with Baseline Seed Job...")
    queue = get_task_queue()
    seed_job = queue.submit_job(
        job_type="document_indexing",
        payload={"task": "initial_seed_indexing", "category": "seed"},
        run_sync=True,
    )
    print(f"  -> Seed job finished with status: {seed_job.status} (Job ID: {seed_job.job_id})")

    print("[5/5] Seed Completed Successfully!")
    print("=================================================================")
    print("HealthTech Demo Credentials:")
    print("  Member Login:  member@healthtech.test / MemberPass123!")
    print("  Admin Login:   admin@healthtech.test  / AdminPass123!")
    print("  Web Portal:    http://localhost:3000")
    print("  API Docs:      http://localhost:8000/api/docs/")
    print("=================================================================")


if __name__ == "__main__":
    seed_database()
