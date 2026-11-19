# gta6-trophy-forecast

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01)

Forecasts each Grand Theft Auto VI PlayStation 5 trophy's earn rate a week after
launch, from the reads a stale public page gave before the checkpoint. Each
trophy's newest printed rate is carried forward in logit space and widened by
`0.125*sqrt(horizon/90)`, which reproduces both reference rows the competition
publishes.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```
