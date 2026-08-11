from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("users", "0002_skill_crewskill")]
    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE users_crewskill
              ADD CONSTRAINT crewskill_tenant_user_fk FOREIGN KEY (tenant_id, user_id)
              REFERENCES users_user (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE;
            ALTER TABLE users_crewskill
              ADD CONSTRAINT crewskill_tenant_skill_fk FOREIGN KEY (tenant_id, skill_id)
              REFERENCES users_skill (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE;
            """,
            reverse_sql="""
            ALTER TABLE users_crewskill DROP CONSTRAINT crewskill_tenant_user_fk;
            ALTER TABLE users_crewskill DROP CONSTRAINT crewskill_tenant_skill_fk;
            """,
        ),
    ]
