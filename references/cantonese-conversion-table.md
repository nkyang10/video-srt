# 廣東話口語 → 香港繁體語體文 Conversion Table

For Cantonese subtitle post-processing (worship/sermon videos).

## Particle Conversions (always apply)

| 口語 | 語體文 | Example (口語 → 語體文) |
|------|--------|------------------------|
| 嘅 | 的 | 我哋嘅神 → 我們的神 |
| 喺 | 在 | 喺祈禱裡面 → 在祈禱裡面 |
| 唔係 | 不是 | 佢唔係先知 → 他不是先知 |
| 哋 | 們 | 我哋 → 我們, 你哋 → 你們, 佢哋 → 他們 |
| 咗 | 了 | 翻咗嚟 → 回來了 |
| 噉/咁 | 這樣/那麼 | 噉樣 → 這樣, 咁我哋 → 那麼我們 |
| 係 | 是 | 佢係好人 → 他是好人 |
| 喺..度 | 在..這裡 | 喺教會度 → 在教會這裡 |
| 喺..嗰度 | 在..那裡 | 喺祈禱嗰度 → 在祈禱那裡 |
| 咧/啦/咯/嘞/㗎 | (remove or comma) | 好咯 → 好, 我哋咧 → 我們, |
| 嘅嘢 | 的東西/的事情 | 佢講嘅嘢 → 他說的事情 |

## Verb & Adjective Conversions

| 口語 | 語體文 | Example |
|------|--------|---------|
| 睇 | 看 | 睇電視 → 看電視 |
| 話 | 說 | 佢話 → 他說 |
| 話畀 | 告訴 | 話畀我知 → 告訴我 |
| 俾/畀 | 給 | 俾我 → 給我 |
| 冇 | 沒有 | 冇時間 → 沒有時間 |
| 有冇 | 有沒有 | 有冇問題 → 有沒有問題 |
| 嚟 | 來 | 翻嚟 → 回來 |
| 去 | (keep) | 去教會 → 去教會 |
| 返/翻 | 回/回到 | 返嚟 → 回來 |
| 諗 | 想/思考 | 我諗 → 我想 |
| 知 | 知道 | 我知 → 我知道 |
| 識 | 懂/會 | 我識 → 我懂 |
| 仲 | 還 | 仲未 → 還沒有 |
| 未 | 還沒有 | 未搞定 → 還沒有完成 |
| 啱啱 | 剛剛 | 啱啱開始 → 剛剛開始 |

## Noun & Pronoun Conversions

| 口語 | 語體文 | Example |
|------|--------|---------|
| 佢 | 他/她/祂(神) | 佢係牧師 → 他是牧師 |
| 呢個 | 這個 | 呢個經文 → 這個經文 |
| 嗰個 | 那個 | 嗰個人 → 那個人 |
| 呢啲 | 這些 | 呢啲問題 → 這些問題 |
| 嗰啲 | 那些 | 嗰啲弟兄姊妹 → 那些弟兄姊妹 |
| 邊個 | 誰 | 邊個講嘅 → 誰說的 |
| 邊度 | 哪裡 | 你去邊度 → 你去哪裡 |
| 點解 | 為什麼 | 點解佢唔嚟 → 為什麼他不來 |
| 點樣 | 怎樣/如何 | 你點樣做到 → 你怎樣做到 |
| 乜嘢/咩 | 什麼 | 你想做乜 → 你想做什麼 |
| 幾時 | 什麼時候 | 你幾時去 → 你什麼時候去 |

## Special Cases

### 神學詞彙保持原樣
- 救贖, 恩典, 信心, 稱義, 成聖, 阿們 → 不轉換
- 耶穌 (not 爺哥/謝穌 → fix ASR error)
- 主啊 (not 煮啊 → fix ASR error)

### 聖經經文
Keep in original written form — do NOT convert to colloquial and do NOT convert back from colloquial if already in written form.

Example — keep as-is:
> 我的恩典夠你用的，因為我的能力是在人的軟弱上顯得完全。

### 人名/地名
- Common English terms (OK, program, meeting): keep as-is
- ASR errors: mtc → (remove, likely a ministry acronym), john → (remove if garbled)

## Line Formatting Rules

1. Max 3 lines per subtitle block
2. Max 25 Chinese characters per line
3. Add commas (，) at natural pauses mid-sentence
4. Do NOT add period (。) at end of sentence
5. Hong Kong Traditional Chinese only
6. Singing/worship blocks: remove entirely, do NOT output
