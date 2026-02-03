# Relationship Memory - Privacy & Ethics

## Privacy First Design

The Relationship Memory System is built with privacy as a foundational principle, not an afterthought.

## Core Privacy Principles

### 1. Local-Only Storage
- **All data stays on your machine**
- No cloud synchronization
- No external API calls
- No telemetry or analytics
- No data transmission

### 2. Complete User Control
- **You own all your data**
- Can view everything stored
- Can export anytime
- Can delete selectively or completely
- Can backup and transfer

### 3. Transparent Operation
- **Open source implementation**
- Human-readable database (SQLite)
- Clear schema documentation
- No hidden data collection
- Auditable code

### 4. Zero Third-Party Access
- **No external dependencies for storage**
- No cloud services
- No authentication servers
- No analytics platforms
- Completely standalone

## What Data Is Stored

### Interaction Records
```python
# Example of what's stored
{
    "user_input": "How do I use async/await?",
    "system_response": "Here's how async/await works...",
    "user_feedback": "Thanks!",
    "interaction_type": "question",
    "context": {
        "task_type": "learning",
        "task_completed": True
    },
    "timestamp": "2026-02-03 10:30:45",
    "sentiment_score": 0.8,
    "success_score": 0.9,
    "love_alignment": 0.85
}
```

### Learned Preferences
```python
{
    "category": "coding_style",
    "preference": "snake_case_naming",
    "strength": 0.85,
    "evidence_count": 12,
    "first_observed": "2026-02-01",
    "last_observed": "2026-02-03"
}
```

### Aggregated Metrics
```python
{
    "metric_date": "2026-02-03",
    "avg_sentiment": 0.75,
    "avg_success_score": 0.82,
    "avg_love_alignment": 0.78,
    "interaction_count": 15,
    "relationship_score": 0.68
}
```

## What Is NOT Stored

- No personally identifiable information (unless you provide it)
- No code contents (only metadata like "used pytest")
- No file paths or system details
- No passwords or credentials
- No network activity
- No IP addresses
- No device identifiers
- No telemetry

## Data Sovereignty

### Your Rights

1. **Right to Access**
   - View all your data anytime
   - Export in readable formats
   - Query the database directly

2. **Right to Delete**
   - Delete entire database
   - Remove specific interactions
   - Clear old data

3. **Right to Export**
   - Export to JSON
   - Export to CSV
   - Copy database file

4. **Right to Transfer**
   - Move database to another machine
   - Share with other tools (your choice)
   - Backup wherever you want

### How to Exercise Your Rights

#### View All Data
```python
from core.relationship_memory import RelationshipMemory

rm = RelationshipMemory()

# View profile
profile = rm.get_user_profile()
print(json.dumps(profile, indent=2))

# View all interactions
history = rm.get_interaction_history(limit=1000)
for interaction in history:
    print(interaction)
```

#### Export Data
```python
import json
from core.relationship_memory import RelationshipMemory

rm = RelationshipMemory()

# Complete export
export_data = {
    'profile': rm.get_user_profile(),
    'interactions': rm.get_interaction_history(limit=10000),
    'growth': rm.measure_relationship_growth(),
    'love_alignment': rm.get_love_alignment_score()
}

# Save to file
with open('my_relationship_memory_export.json', 'w') as f:
    json.dump(export_data, f, indent=2, default=str)

print("Data exported to my_relationship_memory_export.json")
```

#### Delete Data
```python
import sqlite3
import os

# Option 1: Delete entire database
db_path = "relationship_memory.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print("All data deleted")

# Option 2: Delete specific interactions
conn = sqlite3.connect("relationship_memory.db")
c = conn.cursor()

# Delete old interactions
c.execute("""
    DELETE FROM interactions
    WHERE timestamp < date('now', '-30 days')
""")

# Delete specific user
c.execute("DELETE FROM interactions WHERE user_id = ?", ("user_to_delete",))

conn.commit()
conn.close()
print("Selective deletion complete")
```

#### Transfer Data
```bash
# Copy database to new location
cp relationship_memory.db /path/to/backup/

# Transfer to another machine
scp relationship_memory.db user@machine:/path/

# Backup to external drive
cp relationship_memory.db /media/external/backups/
```

## Security Considerations

### Database Security

1. **File Permissions**
   - Database file should have restricted permissions
   - Only your user account should have access

```bash
# Set secure permissions (Unix/Linux/Mac)
chmod 600 relationship_memory.db

# Check permissions
ls -l relationship_memory.db
```

2. **Encryption** (Optional)
   - SQLite supports encryption via SQLCipher
   - Encrypt database file at OS level
   - Use encrypted filesystem

```python
# Example with SQLCipher (requires pysqlcipher3)
from pysqlcipher3 import dbapi2 as sqlite3

conn = sqlite3.connect("encrypted_memory.db")
conn.execute("PRAGMA key = 'your-secure-password'")
# Now use normally
```

3. **Backup Security**
   - Encrypt backups
   - Use secure backup locations
   - Regular backup schedule

### Access Control

```python
# Single-user access
class SecureRelationshipMemory(RelationshipMemory):
    def __init__(self, db_path, user_id, access_key):
        # Verify access key
        if not self._verify_access(access_key):
            raise PermissionError("Invalid access key")
        super().__init__(db_path, user_id)

    def _verify_access(self, key):
        # Implement your access control
        import hashlib
        expected = hashlib.sha256(b"your_secret").hexdigest()
        return key == expected
```

## Ethical Considerations

### The Love Equation and Ethics

Brian Roemmele's Love Equation states: "Love is giving." This system embodies that through:

1. **Respecting User Autonomy**
   - You control what's stored
   - You decide what to share
   - You own your data

2. **Transparent Learning**
   - Clear what's being learned
   - Visible confidence scores
   - Auditable decisions

3. **Beneficial Intent**
   - Goal: Help you better
   - Not: Manipulate or exploit
   - Measure: Your satisfaction

4. **Privacy as Love**
   - Protecting your data = respecting you
   - Local storage = trusting you
   - No surveillance = honoring autonomy

### Consent

The system requires implicit consent through use:

```python
# Explicit consent pattern
class ConsentAwareMemory(RelationshipMemory):
    def __init__(self, db_path, user_id):
        # Check for consent file
        consent_file = f"{db_path}.consent"
        if not os.path.exists(consent_file):
            consent = input("Allow relationship memory? (yes/no): ")
            if consent.lower() != 'yes':
                raise Exception("User declined consent")
            with open(consent_file, 'w') as f:
                f.write(f"Consented at {datetime.now()}")

        super().__init__(db_path, user_id)
```

### Data Minimization

Only store what's necessary:

```python
# Example: Anonymized storage
def record_interaction_anonymized(self, interaction_type, context,
                                 user_feedback, **kwargs):
    # Remove potentially identifying information
    safe_context = {
        k: v for k, v in context.items()
        if k not in ['user_name', 'email', 'ip_address', 'file_path']
    }

    # Store with minimal data
    return self.record_interaction(
        interaction_type=interaction_type,
        context=safe_context,
        user_feedback=user_feedback[:100],  # Limit length
        user_input="",  # Don't store full input
        system_response=""  # Don't store full response
    )
```

### Purpose Limitation

Data used only for stated purpose:

```python
# Clear purpose statement
PURPOSE = """
This Relationship Memory System collects interaction data for the sole
purpose of:
1. Learning your preferences
2. Adapting assistance to your style
3. Measuring improvement in help quality

Data is NOT used for:
- Marketing or advertising
- User profiling for other purposes
- Sale or transfer to third parties
- Training general AI models
- Any purpose not stated above
"""

def get_purpose_statement():
    return PURPOSE
```

## Multi-User Considerations

### Separate Databases

```python
# Each user gets their own database
def get_user_memory(username):
    db_path = f"memories/{username}_memory.db"
    return RelationshipMemory(db_path=db_path, user_id=username)

# User A
alice_memory = get_user_memory("alice")

# User B
bob_memory = get_user_memory("bob")

# Completely separate - no cross-contamination
```

### Shared System, Private Data

```python
# Same database, isolated users
class IsolatedMemory(RelationshipMemory):
    def get_user_profile(self):
        # Only return this user's data
        profile = super().get_user_profile()
        if profile['user_id'] != self.user_id:
            raise PermissionError("Cannot access other user's data")
        return profile

    def get_interaction_history(self, limit=50, interaction_type=None):
        # Filter to current user only
        history = super().get_interaction_history(limit, interaction_type)
        return [h for h in history if h['user_id'] == self.user_id]
```

## Compliance Considerations

### GDPR-Style Compliance

Even though this is local-only, here's how it would comply:

1. **Right to Access** ✓ - Full data export
2. **Right to Rectification** ✓ - Can modify database
3. **Right to Erasure** ✓ - Can delete data
4. **Right to Data Portability** ✓ - JSON/CSV export
5. **Right to Object** ✓ - Don't use the system
6. **Data Minimization** ✓ - Only stores necessary data
7. **Purpose Limitation** ✓ - Clear stated purpose
8. **Storage Limitation** ✓ - Can set retention policies

### Retention Policy

```python
# Automatic data retention
class RetentionPolicyMemory(RelationshipMemory):
    def __init__(self, db_path, user_id, retention_days=90):
        super().__init__(db_path, user_id)
        self.retention_days = retention_days
        self._apply_retention_policy()

    def _apply_retention_policy(self):
        """Delete data older than retention period"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=self.retention_days)).isoformat()

        c.execute("""
            DELETE FROM interactions
            WHERE user_id = ? AND timestamp < ?
        """, (self.user_id, cutoff_date))

        conn.commit()
        conn.close()
```

## Best Practices

### For Users

1. **Regular Backups**
   ```bash
   # Cron job for daily backups
   0 0 * * * cp ~/.openclaw/relationship_memory.db ~/backups/memory_$(date +\%Y\%m\%d).db
   ```

2. **Periodic Reviews**
   ```python
   # Monthly data review
   profile = rm.get_user_profile()
   history = rm.get_interaction_history(limit=100)

   print("Review your data:")
   print(f"  Total interactions: {profile['total_interactions']}")
   print(f"  Learned preferences: {len(profile['learned_preferences'])}")
   print("  Consider deleting old data if desired")
   ```

3. **Secure Storage**
   - Use encrypted filesystem
   - Restrict file permissions
   - Regular security updates

### For Developers

1. **Minimize Data Collection**
   ```python
   # Only collect what's needed
   context = {
       "task_type": task_type,  # Essential
       "task_completed": completed,  # Essential
       # Don't include: file_path, full_code, user_email, etc.
   }
   ```

2. **Sanitize Inputs**
   ```python
   def sanitize_feedback(feedback):
       """Remove potentially sensitive information"""
       # Remove email addresses
       import re
       feedback = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                        '[EMAIL]', feedback)
       # Remove paths
       feedback = re.sub(r'[A-Za-z]:\\[\\\S|*\S]?.*', '[PATH]', feedback)
       # Remove URLs
       feedback = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                        '[URL]', feedback)
       return feedback
   ```

3. **Audit Logging**
   ```python
   # Log data access for audit trail
   def log_access(operation, user_id):
       with open('access_log.txt', 'a') as f:
           f.write(f"{datetime.now()}: {operation} by {user_id}\n")
   ```

## Summary

The Relationship Memory System is designed with privacy as a core value:

- **Local storage only** - Your data never leaves your machine
- **Complete control** - View, export, delete anytime
- **Transparent** - Open source, readable database
- **Ethical** - Respects autonomy, minimizes data
- **Secure** - Supports encryption, access control

This embodies the Love Equation: **respecting your privacy is respecting you**, which is a form of love.

## Questions?

- Review the code: `core/relationship_memory.py`
- Check tests: `tests/test_relationship_memory.py`
- Read docs: `docs/RELATIONSHIP_MEMORY.md`
- Run demo: `python demo_relationship_memory.py`

Remember: **Your data, your control, your privacy.** Always.
