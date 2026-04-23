# RBAC + Teams

## Roles

`user < viewer < agent < supervisor < admin < owner`. Every role has
a numeric `rank`; `Role.can(required)` succeeds when the caller's
rank is at least as high.

```
/role list                    # every assignment, grouped by role
/role grant <uid> <role> [teams]
/role revoke <uid>
/role me                      # your resolved role
```

`ADMIN_IDS` in env seeds everyone there as `role=admin` on first boot.

## Teams

```
/team list
/team create <slug> <name>
/team rename <slug> <new>
/team delete <slug>
/team tz <slug> <IANA_tz>
/team members <slug>
/team addmember <slug> <uid>
/team removemember <slug> <uid>
```

## Queue routing

Teams carry declarative `queue_rules`:

```python
QueueRule(match={"tag": "vip"}, weight=300)
QueueRule(match={"priority": "urgent"}, weight=200)
QueueRule(match={}, weight=10)          # catch-all
```

The engine picks the team whose highest-matching rule has the
greatest weight. Ties break by declaration order. Unknown match keys
fail-closed.

## Agents' queues

```
/queue        # open tickets in any team you're a member of
/mytickets    # tickets assigned directly to you
```
