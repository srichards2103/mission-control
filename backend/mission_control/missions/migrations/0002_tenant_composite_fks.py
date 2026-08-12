from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("missions", "0001_initial")]
    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE missions_missionrequirement
              ADD CONSTRAINT requirement_tenant_mission_fk FOREIGN KEY (tenant_id, mission_id)
              REFERENCES missions_mission (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE;
            ALTER TABLE missions_missionrequirement
              ADD CONSTRAINT requirement_tenant_skill_fk FOREIGN KEY (tenant_id, skill_id)
              REFERENCES users_skill (tenant_id, id) DEFERRABLE INITIALLY IMMEDIATE;
            """,
            reverse_sql="""
            ALTER TABLE missions_missionrequirement DROP CONSTRAINT requirement_tenant_mission_fk;
            ALTER TABLE missions_missionrequirement DROP CONSTRAINT requirement_tenant_skill_fk;
            """,
        ),
    ]
