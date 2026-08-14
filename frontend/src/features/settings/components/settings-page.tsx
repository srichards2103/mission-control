import { PageHeader } from "@/components/ui/page-header";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OrganisationTab } from "@/features/settings/components/organisation-tab";
import { SkillsTab } from "@/features/settings/components/skills-tab";
import { UsersTab } from "@/features/settings/components/users-tab";

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Settings" />
      <Tabs defaultValue="users">
        <TabsList variant="line">
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="organisation">Organisation</TabsTrigger>
        </TabsList>
        <TabsContent value="users">
          <UsersTab />
        </TabsContent>
        <TabsContent value="skills">
          <SkillsTab />
        </TabsContent>
        <TabsContent value="organisation">
          <OrganisationTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
