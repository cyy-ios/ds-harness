# Local Environment

Do not commit secret values.

DeepSeek key lookup order:

1. `$env:DEEPSEEK_API_KEY`
2. `$env:DEEPSEEK_API_KEY_FILE`
3. local workstation key file: `C:\Users\cuiyi\token\deepseek-api-key.txt`

Preferred local setup:

```powershell
$env:DEEPSEEK_API_KEY_FILE = 'C:\Users\cuiyi\token\deepseek-api-key.txt'
```

Agents should check this file path before asking the user for a token. Never print the file contents.
