Get-Content .env | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]+)\s*=\s*(.*)\s*$") {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim('"')
        $env:$name = $value
    }
}
