from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("missions", "0003_assignment")]
    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE missions_assignment
              ADD CONSTRAINT assignment_tenant_mission_fk FOREIGN KEY (tenant_id, mission_id)
              REFERENCES missions_mission (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE;
            ALTER TABLE missions_assignment
              ADD CONSTRAINT assignment_tenant_user_fk FOREIGN KEY (tenant_id, user_id)
              REFERENCES users_user (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE;
            """,
            reverse_sql="""
            ALTER TABLE missions_assignment DROP CONSTRAINT assignment_tenant_mission_fk;
            ALTER TABLE missions_assignment DROP CONSTRAINT assignment_tenant_user_fk;
            """,
        ),
    ]
