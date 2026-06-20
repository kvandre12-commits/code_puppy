"""Knowledge base for the Android App Doctor.

Maps crash/exception signatures to a plain-English diagnosis:
  - what  : what actually went wrong, in human terms
  - fix   : the concrete change to make
  - why   : WHY that fix works / why it broke (the part developers rarely get)

This is the "why machine." Each entry is matched against the exception type
and (optionally) the message text. First match wins; a generic fallback
always applies so the doctor never shrugs.
"""

from __future__ import annotations

# Each rule: (type_substr, msg_substr_or_empty, what, fix, why)
RULES: list[tuple[str, str, str, str, str]] = [
    (
        "NullPointerException",
        "",
        "The app tried to use an object that was null (nothing there).",
        "Find the variable on the crash line and guard it before use: "
        "check for null (Java) or use a safe-call `?.` / Elvis `?:` (Kotlin). "
        "Often the real fix is upstream: figure out WHY it was null "
        "(a view not yet inflated, an async result not arrived, a missing "
        "intent extra).",
        "A null reference means the object was never assigned, was cleared, "
        "or the data you expected didn't show up. The crash line tells you "
        "WHERE it blew up, but the root cause is wherever that value was "
        "supposed to be set. Null-checking hides the symptom; fixing the "
        "source removes it.",
    ),
    (
        "NetworkOnMainThreadException",
        "",
        "The app did network work on the main (UI) thread.",
        "Move the network/IO call off the main thread: a coroutine on "
        "Dispatchers.IO, an Executor, WorkManager, or RxJava background "
        "scheduler. Never touch the network from the UI thread.",
        "Android forbids network on the main thread because it freezes the "
        "screen while waiting for the response, which causes jank and ANRs. "
        "The OS throws on purpose to force you to background it.",
    ),
    (
        "ActivityNotFoundException",
        "",
        "The app fired an Intent that no installed app can handle.",
        "Verify the Intent action/data/MIME, confirm a target app exists, "
        "and on Android 11+ add a <queries> entry in the manifest. Guard the "
        "launch with `intent.resolveActivity(packageManager) != null`.",
        "Intents are resolved at runtime against whatever apps are installed. "
        "If nothing matches (wrong action, missing app, or package "
        "visibility blocked by Android 11+ scoping), the system can't route "
        "it and throws. Checking resolvability first prevents the crash.",
    ),
    (
        "SecurityException",
        "permission",
        "The app used a feature it doesn't have permission for.",
        "Declare the permission in AndroidManifest.xml AND request it at "
        "runtime (for dangerous permissions) before the call. Handle the "
        "denied case gracefully.",
        "Android gates sensitive features (camera, location, contacts...) "
        "behind permissions. A manifest entry alone isn't enough for "
        "dangerous permissions since Android 6 - the user must grant it at "
        "runtime, or the call is blocked.",
    ),
    (
        "SecurityException",
        "",
        "The app tried something the OS blocked for security reasons.",
        "Read the message for the exact restriction. Common causes: missing "
        "permission, accessing another app's data, or a background-activity/"
        "exact-alarm restriction on newer Android.",
        "The OS enforces sandboxing and permission boundaries. A "
        "SecurityException is Android refusing an operation that crosses "
        "those lines.",
    ),
    (
        "IllegalStateException",
        "Fragment",
        "The app touched a Fragment that wasn't attached / was destroyed.",
        "Guard UI work with `isAdded`/`viewLifecycleOwner`, and don't commit "
        "fragment transactions after onSaveInstanceState. Cancel async "
        "callbacks in onDestroyView.",
        "Fragments have a lifecycle. If an async result arrives after the "
        "Fragment detached (rotation, navigation), its views are gone, so "
        "touching them is illegal. Lifecycle-aware scopes prevent the "
        "stale callback.",
    ),
    (
        "OutOfMemoryError",
        "",
        "The app ran out of memory (usually huge bitmaps or a leak).",
        "Downsample images with inSampleSize / use Glide/Coil, recycle "
        "bitmaps, and hunt leaks with LeakCanary. Avoid holding Context/View "
        "references in static fields or long-lived objects.",
        "Each app gets a capped heap. Loading full-resolution images or "
        "leaking Activities (which retain their whole view tree) exhausts it. "
        "The fix is to use less memory and release it promptly.",
    ),
    (
        "ClassCastException",
        "",
        "The app assumed an object was one type but it was another.",
        "Check the cast on the crash line; validate with `is`/`instanceof` "
        "before casting, or fix the source that produced the wrong type "
        "(e.g., a findViewById returning the wrong view, or bad JSON "
        "deserialization).",
        "Casting tells the compiler to trust you about a type. If the real "
        "object doesn't match at runtime, the JVM refuses. The wrong type "
        "usually originates earlier - that's the real bug.",
    ),
    (
        "NumberFormatException",
        "",
        "The app tried to turn text into a number, but the text wasn't one.",
        "Validate/trim input before parsing and use a safe parse "
        "(Kotlin `toIntOrNull()`), defaulting or erroring cleanly on bad "
        "input.",
        "Parsing assumes well-formed input. Empty strings, locale decimal "
        "marks, or stray characters break it. Defensive parsing turns a "
        "crash into a handled case.",
    ),
    (
        "IndexOutOfBoundsException",
        "",
        "The app accessed a list/array position that doesn't exist.",
        "Check the index against size before access; confirm the collection "
        "isn't empty or smaller than expected, especially after async "
        "updates or filtering.",
        "Indices are zero-based and bounded by size. Off-by-one logic or a "
        "collection that changed underneath you produces an out-of-range "
        "access, which the runtime rejects.",
    ),
    (
        "BadTokenException",
        "",
        "The app showed a dialog/window on a dead or wrong Activity.",
        "Only show dialogs on a valid, resumed Activity context (not "
        "application context), and dismiss them in onDestroy/onPause to "
        "avoid leaking a window after the Activity is gone.",
        "Windows attach to an Activity's token. If that Activity finished or "
        "you used the wrong context, there's no valid token, so the "
        "WindowManager refuses to draw.",
    ),
    (
        "SQLiteException",
        "",
        "A database operation failed (bad query, schema, or migration).",
        "Check the SQL/message; for 'no such column/table' it's usually a "
        "missing migration. Bump the DB version and supply a migration path "
        "instead of crashing existing installs.",
        "SQLite enforces its schema. When app code expects columns/tables "
        "the on-device DB doesn't have (because the user upgraded without a "
        "migration), queries fail. Migrations reconcile old data with new "
        "code.",
    ),
]

ANR_DIAG = (
    "The app's main thread was blocked too long, so Android flagged it Not Responding.",
    "Move the slow work (network, disk, big loops, locks) off the main "
    "thread. Find what the 'main' thread was doing in the ANR trace and "
    "background it.",
    "The UI thread must stay free to draw and handle input. If it's busy "
    "for ~5s, the user sees a frozen app, so Android offers to kill it. "
    "Keeping the main thread light is the only real fix.",
)

NATIVE_DIAG = (
    "A native (C/C++) crash - the app hit an illegal memory operation.",
    "Look at the signal (SIGSEGV = bad memory access, SIGABRT = an assert/"
    "abort). Inspect the native library named in the backtrace; check for "
    "null pointers, buffer overruns, or use-after-free in the NDK code.",
    "Native code has no garbage collector or bounds checking. A bad pointer "
    "or overrun corrupts memory and the kernel kills the process with a "
    "fatal signal. The backtrace points at the offending library.",
)

GENERIC_DIAG = (
    "The app threw an unhandled exception and crashed.",
    "Open the first stack frame that points at the app's own code (not "
    "android.*/java.*/kotlin.*) - that's the line to fix. Read the exception "
    "message; it usually states exactly what went wrong.",
    "An uncaught exception unwinds to the top and the OS kills the process. "
    "Framework frames show the path, but YOUR code frame is where the bad "
    "assumption lives. Wrapping it in try/catch only helps if you also "
    "handle the real cause.",
)


def diagnose(exc_type: str, message: str) -> dict[str, str]:
    """Return {what, fix, why} for an exception type + message."""
    t = exc_type or ""
    m = (message or "").lower()
    for type_sub, msg_sub, what, fix, why in RULES:
        if type_sub.lower() in t.lower() and (not msg_sub or msg_sub.lower() in m):
            return {"what": what, "fix": fix, "why": why}
    what, fix, why = GENERIC_DIAG
    return {"what": what, "fix": fix, "why": why}
