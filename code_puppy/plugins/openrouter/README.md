# OpenRouter Plugin

This built-in plugin wires Code Puppy to OpenRouter using one API key:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

Do not commit or paste the key. The plugin only references it as:

```json
"api_key": "$OPENROUTER_API_KEY"
```

## Default aliases

When enabled, the plugin injects these model aliases:

- `openrouter-auto`
- `openrouter-sonnet`
- `openrouter-gpt-mini`
- `openrouter-qwen-coder`
- `openrouter-cycle`

`openrouter-cycle` is a round-robin alias across the configured OpenRouter model aliases.

## Custom aliases

Override/add aliases without editing code:

```bash
export CODE_PUPPY_OPENROUTER_MODELS="primary=anthropic/claude-sonnet-4.5,fast=openrouter/auto"
```

Optional context length suffix:

```bash
export CODE_PUPPY_OPENROUTER_MODELS="primary=anthropic/claude-sonnet-4.5:200000"
```

Disable presets:

```bash
export CODE_PUPPY_OPENROUTER_INCLUDE_PRESETS=0
```

Adjust round-robin interval:

```bash
export CODE_PUPPY_OPENROUTER_ROTATE_EVERY=3
```

## Status command

Inside Code Puppy:

```text
/openrouter-status
```

This reports whether the key is configured and lists OpenRouter aliases without printing the secret.
