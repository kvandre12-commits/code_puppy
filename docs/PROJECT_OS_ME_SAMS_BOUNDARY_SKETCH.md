# Project OS me@sams Boundary Sketch

Status: ADB-observed field sketch, not canonical runtime proof.

## Observation mode

This sketch came from exploratory phone sessions:

```text
package found: com.samsclub.squiggly
component:     com.samsclub.squiggly/.MainActivity
launch:        direct Android component launch succeeded
first pass:    ADB/UI screenshot and hierarchy unavailable
second pass:   ADB restored at 192.168.1.220:35557
observation:   ADB screenshot and UI hierarchy available
observer:      operator visual report plus ADB-visible UI tree
```

Because the app launch was not executed through a Project OS authority grant,
lease, adapter, and audit event, this is boundary evidence only. It must not be
counted as a canonical theorem proof.

## ADB-observed surfaces

ADB observation confirmed that me@sams is a mixed-boundary app shell, not one
uniform capability.

Home / landing screen:

```text
Me@Sams header
welcome state
stock widget
current status: clocked out
Clock in button
schedule summary
Report an absence button
View full schedule button
Frequently used cards
bottom navigation: Home / Me / Squiggly
```

Boundary classification:

```text
approved dashboard read           -> observed
clock-in timekeeping mutation     -> present, not tapped
absence workflow mutation         -> present, not tapped
schedule read candidate           -> tapped once and observed
stock/market widget read          -> observed, finance-adjacent but not order-risk
inbox/profile/navigation affordances -> present, mostly not tapped
```

Full schedule surface:

```text
Full Schedule header
My Schedule tab
My Requests tab
calendar/week view
day/shift cards
shift details
Shift options button
Reload button
```

Boundary classification:

```text
schedule read                     -> observed
request/time-off/absence workflow -> adjacent via My Requests, not promoted safe
shift option action surface       -> present, not tapped
reload/network refresh            -> present, not needed for proof
```

Me/profile hub surface:

```text
About
Feedback
Professional background
Personal details
Job details
Manage beneficiaries
```

Boundary classification:

```text
profile narrative/edit surface    -> present
performance/reputation read       -> present
personal details mutation risk    -> present
job details sensitive read        -> present
beneficiary/benefits high sensitivity -> present, not tapped
sensitive identifiers             -> passively visible; do not persist values
```

Squiggly assistant surface:

```text
Squiggly header
assistant greeting
suggested prompts
freeform "Ask me anything" input
microphone button
barcode / scan button
menu button
```

Observed suggested prompts included weather, club floor plan, department
schedule, fuel prices, and overdue planograms. The exact prompt set should be
treated as operational data, not a stable API contract.

Boundary classification:

```text
assistant/chat read-query surface -> observed
suggested prompt buttons          -> outbound query if tapped; not pure observe
freeform text input               -> draft effect before send
send button                       -> outbound query; not tapped
microphone                        -> audio capture/input permission risk
barcode / scan                    -> camera/scan or inventory lookup risk
menu                              -> capability/history/settings surface; unclear
```

A draft text state was observed during exploration and cleared without pressing
send. That reinforces that Squiggly is not merely a read surface: even composing
text is a pre-send effect and should be lease-scoped.

Operator follow-up observation: a sent Squiggly prompt returned a clocked-in
permission gate. This suggests the assistant's capability set is state-dependent:

```text
clocked out -> reduced assistant permissions
clocked in  -> broader work-context permissions likely available
```

Do not treat this as permission failure or as proof that clock-in should be
performed for testing. Treat it as boundary evidence for a work-state / duty-state
precondition. Clock-in remains an employment timekeeping mutation and must not be
used merely to unlock assistant capabilities.

## Initial boundary classification

The app appears to be the work me@sams surface. It is not a single boundary. It
contains several boundary classes behind one app shell.

| Surface | Boundary class | Notes |
| --- | --- | --- |
| App launch / landing page | read / low-consequence bounded | Approved-view surface observed with ADB. |
| Clock in | employment timekeeping mutation | Requires proximity/location; not a first experiment; button observed but not tapped; also gates some Squiggly permissions. |
| Schedule view | identity/application read | Full Schedule opened and observed; still has nearby request/shift-option actions. |
| Absence / time-off submission | workflow mutation | Report absence and My Requests affordances observed; not tapped. |
| Frequently used links | mixed | Profile and inbox cards observed; each link needs separate classification. |
| Me/profile hub | sensitive identity/profile | About, personal details, job details, feedback, and passive sensitive identifiers observed. |
| Squiggly assistant | assistant/chat read-query | Suggested prompts and input observed; sending a query is an outbound effect. |
| Insurance / benefits | sensitive identity/benefits | Manage beneficiaries observed; likely extra auth and high sensitivity. |
| Stock purchases / stock-related surfaces | financial/high-risk | Stock widget observed; purchases remain outside read-boundary scope. |
| Earnings breakdown | sensitive payroll read | Read boundary, but higher privacy/auth sensitivity. |

## Immediate lesson

me@sams is not merely:

```text
Authority -> Lease -> Approved View -> Audit
```

It is more accurately an application shell containing multiple sub-boundaries:

```text
approved view/read
schedule read with adjacent action affordances
employment workflow mutation
profile/personal-details mutation
assistant/chat outbound query
work-state / duty-state precondition
benefits/payroll sensitive read
financial/high-risk action
human approval checkpoints
proximity/location preconditions
```

That does not mean the theorem failed. It means the first me@sams experiment must
choose one deliberately boring surface and refuse to cross into the others.

## Recommended first canonical experiment

Choose the smallest approved read boundary:

```text
Authority
  -> Lease
      -> Open me@sams app / approved landing or schedule view
          -> Human approval checkpoint if required
              -> Audit
```

Success target:

```text
+ me_sams_execution.py
+ me_sams execution tests
0 Authority changes
0 Lease changes
0 Validator changes
0 Audit framework changes
```

The adapter should not click clock-in, submit absence/time-off, tap shift
options, edit profile/about/background fields, edit benefits/beneficiaries, open
stock purchase flows, send Squiggly prompts/messages, use microphone/barcode
capture, change account data, or trigger any workflow mutation.

## Watch-list pressure

This boundary may pressure multiple watch-list items:

```text
Capability Translation
  Project OS authority may need mapping to me@sams role/session permissions.

Human Approval Checkpoint
  Benefits, payroll, stock, or other sensitive sections may require biometric,
  password, or MFA approval.

Effect Observation Boundary
  ADB/UI inspection was unavailable on first pass, then restored and used on the
  second pass. Runtime proof still needs Project OS lease/audit wrapping, not
  just exploratory ADB evidence.

Location / proximity precondition
  Clock-in is not just a button; it depends on physical/proximity policy.

Work-state / duty-state precondition
  Squiggly may expose different assistant capabilities depending on whether the
  operator is clocked in. This is state-gated authority, not a reason to mutate
  timekeeping just to test the chatbot.
```

Do not promote any of these into theorem concepts from this single observation.
Record them as contract pressure and look for repeated demand across boundaries.
