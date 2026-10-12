param([string]$TextBase64,[string]$VoiceName,[string]$OutputFile,[switch]$ListVoices)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$speaker=New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices=@($speaker.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -like 'zh-*' })
    if ($ListVoices) { @($voices | ForEach-Object { $_.VoiceInfo.Name }) | ConvertTo-Json -Compress; exit 0 }
    if (!$voices.Count) { throw 'No Chinese Windows desktop speech voice installed. Add Chinese text-to-speech in Windows language settings.' }
    if ($VoiceName) { $speaker.SelectVoice($VoiceName) } else { $speaker.SelectVoice($voices[0].VoiceInfo.Name) }
    $speaker.SetOutputToWaveFile($OutputFile)
    $speaker.Speak([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($TextBase64)))
} finally { $speaker.Dispose() }
