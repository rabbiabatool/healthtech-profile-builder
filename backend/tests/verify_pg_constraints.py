"""
verify_pg_constraints.py
========================
Run with: python manage.py shell < tests/verify_pg_constraints.py
Queries the PostgreSQL system catalog to verify that the expected
constraints, indexes, and nullability rules are physically present.
"""
import json
from django.db import connection

RESULTS = {}
cursor = connection.cursor()


def capture(name, sql):
    cursor.execute(sql)
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    RESULTS[name] = {"sql": sql, "columns": cols, "rows": [dict(zip(cols, row)) for row in rows]}


# --- PostgreSQL version ---
capture("pg_version", "SELECT version();")

# --- Foreign keys on profile-related tables ---
capture(
    "foreign_keys",
    """
    SELECT tc.table_name, tc.constraint_name, kcu.column_name,
           ccu.table_name AS foreign_table
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
         ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
         ON tc.constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name IN ('health_profiles', 'profile_demographics',
                            'wellness_preferences', 'emergency_contacts',
                            'audit_events')
    ORDER BY tc.table_name, tc.constraint_name;
    """,
)

# --- Check constraints ---
capture(
    "check_constraints",
    """
    SELECT conrelid::regclass AS table_name, conname, pg_get_constraintdef(oid) AS definition
    FROM pg_constraint
    WHERE contype = 'c'
      AND conrelid::regclass::text IN ('health_profiles', 'profile_demographics',
                                       'wellness_preferences', 'emergency_contacts',
                                       'audit_events')
    ORDER BY conrelid::regclass::text, conname;
    """,
)

# --- Unique constraints ---
capture(
    "unique_constraints",
    """
    SELECT conrelid::regclass AS table_name, conname, pg_get_constraintdef(oid) AS definition
    FROM pg_constraint
    WHERE contype = 'u'
      AND conrelid::regclass::text IN ('health_profiles', 'profile_demographics',
                                       'wellness_preferences', 'emergency_contacts')
    ORDER BY conrelid::regclass::text, conname;
    """,
)

# --- Indexes ---
capture(
    "indexes",
    """
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE tablename IN ('health_profiles', 'profile_demographics',
                        'wellness_preferences', 'emergency_contacts',
                        'audit_events')
    ORDER BY tablename, indexname;
    """,
)

# --- Column nullability for key tables ---
capture(
    "column_nullability",
    """
    SELECT table_name, column_name, is_nullable, data_type, column_default
    FROM information_schema.columns
    WHERE table_name IN ('health_profiles', 'profile_demographics',
                         'wellness_preferences', 'emergency_contacts',
                         'audit_events')
    ORDER BY table_name, ordinal_position;
    """,
)

# --- audit_events profile_id is NOT a FK (it is a plain BigInteger) ---
capture(
    "audit_profile_id_not_fk",
    """
    SELECT COUNT(*) AS fk_count
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
         ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = 'audit_events'
      AND kcu.column_name = 'profile_id';
    """,
)

# --- Row counts ---
capture(
    "row_counts",
    """
    SELECT 'health_profiles' AS t, COUNT(*) FROM health_profiles
    UNION ALL
    SELECT 'profile_demographics', COUNT(*) FROM profile_demographics
    UNION ALL
    SELECT 'wellness_preferences', COUNT(*) FROM wellness_preferences
    UNION ALL
    SELECT 'emergency_contacts', COUNT(*) FROM emergency_contacts
    UNION ALL
    SELECT 'audit_events', COUNT(*) FROM audit_events;
    """,
)

cursor.close()
print(json.dumps(RESULTS, indent=2, default=str))

