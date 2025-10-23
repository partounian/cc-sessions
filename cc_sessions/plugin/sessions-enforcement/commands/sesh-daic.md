# sesh-daic

Toggle and inspect DAIC mode.

## Usage

- /sesh-daic status — show current mode (discussion/implementation)
- /sesh-daic stop — force return to discussion mode

## Behavior

- In discussion mode, write-like tools are blocked by enforcement hooks
- In implementation mode, remember to return to discussion when done (daic command)

> Implementation detail: This plugin surfaces the existing cc-sessions enforcement; the underlying logic remains in hooks.
