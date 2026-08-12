import { useState } from "react";
import { PencilIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useOrganisation, useUpdateOrganisation } from "@/features/settings/api/settings";
import { errorMessage } from "@/lib/api-errors";

export function OrganisationTab() {
  const { data: organisation, isLoading, isError } = useOrganisation();
  const updateOrganisation = useUpdateOrganisation();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading organisation…</p>;
  if (isError || !organisation) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load the organisation. Please try again.
      </p>
    );
  }

  function startEditing() {
    setName(organisation!.name);
    setEditing(true);
  }

  async function handleSave() {
    try {
      await updateOrganisation.mutateAsync({ name });
      setEditing(false);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-2">
      <span className="text-sm font-medium text-muted-foreground">Organisation name</span>
      {editing ? (
        <div className="flex items-center gap-2">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Organisation name"
            autoFocus
          />
          <Button size="sm" onClick={handleSave} disabled={updateOrganisation.isPending}>
            Save
          </Button>
          <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="text-base">{organisation.name}</span>
          <Button size="icon-sm" variant="ghost" aria-label="Edit organisation name" onClick={startEditing}>
            <PencilIcon />
          </Button>
        </div>
      )}
    </div>
  );
}
