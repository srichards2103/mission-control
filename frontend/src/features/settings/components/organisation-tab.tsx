import { useState } from "react";
import { PencilIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SectionLabel } from "@/components/ui/page-header";
import { useOrganisation, useUpdateOrganisation } from "@/features/settings/api/settings";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-errors";

export function OrganisationTab() {
  const { data: organisation, isLoading, isError } = useOrganisation();
  const updateOrganisation = useUpdateOrganisation();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});

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
    setFieldErrors({});
    setEditing(true);
  }

  async function handleSave() {
    setFieldErrors({});
    try {
      await updateOrganisation.mutateAsync({ name });
      setEditing(false);
    } catch (err) {
      setFieldErrors(fieldErrorsFrom(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <div className="flex max-w-sm flex-col gap-2">
      <SectionLabel>Organisation name</SectionLabel>
      {editing ? (
        <div className="flex flex-col gap-1.5">
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
          {fieldErrors.name && <FieldError>{fieldErrors.name.join(" ")}</FieldError>}
          {fieldErrors.non_field_errors && (
            <FieldError>{fieldErrors.non_field_errors.join(" ")}</FieldError>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="text-sm">{organisation.name}</span>
          <Button size="icon-sm" variant="ghost" aria-label="Edit organisation name" onClick={startEditing}>
            <PencilIcon />
          </Button>
        </div>
      )}
    </div>
  );
}
