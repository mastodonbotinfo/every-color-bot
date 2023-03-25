# Every Color Bot

This bot posts all 16.8 million 24-bit colours to Mastodon, 1 per hour, potentially for 1914 years starting 2023.

Author: https://mastodon.social/@dig

It copies the concept from https://twitter.com/everycolorbot by https://mastodon.social/@vogon but reuses no code.

Rather than use a Linear Feedback Shift Register from the original we use numpy to create a deterministic permuted set of 2^24 colors.

The script is designed to be run every day from a GitHub action, maintaining a schedule of pre-submitted posts.