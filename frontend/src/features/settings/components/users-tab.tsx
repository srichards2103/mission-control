import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useCreateUser, useOrgUsers, useUpdateUser, type OrgUser } from "@/features/settings/api/settings";
import { errorMessage, fieldErrorsFrom } from "@/lib/api-errors";
import { ROLE_OPTIONS, roleLabel } from "@/lib/roles";

function AddUserDialog() {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<OrgUser["role"]>("crew_member");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const createUser = useCreateUser();

  function reset() {
    setEmail("");
    setName("");
    setPassword("");
    setRole("crew_member");
    setFieldErrors({});
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFieldErrors({});
    try {
      await createUser.mutateAsync({ email, name, password, role });
      reset();
      setOpen(false);
    } catch (err) {
      setFieldErrors(fieldErrorsFrom(err));
      toast.error(errorMessage(err));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) reset();
      }}
    >
      <DialogTrigger render={<Button />}>Add user</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add user</DialogTitle>
          <DialogDescription>Invite a new crew member, lead, or director.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-name">Name</Label>
            <Input id="new-user-name" value={name} onChange={(e) => setName(e.target.value)} required />
            {fieldErrors.name && <p className="text-sm text-destructive">{fieldErrors.name.join(" ")}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-email">Email</Label>
            <Input
              id="new-user-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            {fieldErrors.email && <p className="text-sm text-destructive">{fieldErrors.email.join(" ")}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-password">Password</Label>
            <Input
              id="new-user-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            {fieldErrors.password && (
              <p className="text-sm text-destructive">{fieldErrors.password.join(" ")}</p>
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="new-user-role">Role</Label>
            <Select value={role} onValueChange={(value) => setRole(value as OrgUser["role"])}>
              <SelectTrigger id="new-user-role">
                <SelectValue>{(value: OrgUser["role"]) => roleLabel(value)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={createUser.isPending}>
              {createUser.isPending ? "Adding…" : "Add user"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RoleSelect({ user }: { user: OrgUser }) {
  const updateUser = useUpdateUser();
  return (
    <Select
      value={user.role}
      onValueChange={(value) =>
        updateUser.mutate(
          { id: user.id, role: value as OrgUser["role"] },
          { onError: (err) => toast.error(errorMessage(err)) },
        )
      }
    >
      <SelectTrigger size="sm" aria-label={`Role for ${user.name}`}>
        <SelectValue>{(value: OrgUser["role"]) => roleLabel(value)}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {ROLE_OPTIONS.map((r) => (
          <SelectItem key={r.value} value={r.value}>
            {r.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function UsersTab() {
  const { data: users, isLoading, isError } = useOrgUsers();
  const updateUser = useUpdateUser();

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading users…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load users. Please try again.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <AddUserDialog />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Status</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {users?.map((user) => (
            <TableRow key={user.id} className={user.is_active ? undefined : "opacity-50"}>
              <TableCell>{user.name}</TableCell>
              <TableCell>{user.email}</TableCell>
              <TableCell>
                <Badge variant="secondary">{roleLabel(user.role)}</Badge>
              </TableCell>
              <TableCell>
                <Badge variant={user.is_active ? "secondary" : "outline"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <RoleSelect user={user} />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      updateUser.mutate(
                        { id: user.id, is_active: !user.is_active },
                        { onError: (err) => toast.error(errorMessage(err)) },
                      )
                    }
                  >
                    {user.is_active ? "Deactivate" : "Reactivate"}
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
