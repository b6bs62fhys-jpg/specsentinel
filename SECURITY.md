# Security Policy

## Supported versions

The latest release is supported with security fixes. Older releases may not get
one, so please reproduce the issue on the newest version before reporting.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Use GitHub's private vulnerability reporting: open the **Security** tab of the
repository and choose **Report a vulnerability**. That keeps the report private
until a fix is ready.

Include:

* the affected version (from `specsentinel --version`),
* what you did, step by step,
* what happened and what you expected,
* the impact you think it has.

You will get an answer as soon as possible. This is a small project without a
formal response time, but reports are taken seriously.

## Specs and references

SpecSentinel follows `$ref` across files and URLs. A spec can therefore make
SpecSentinel read files from the machine it runs on and fetch documents from any
URL it can reach. Only check specs you trust: review a spec before running it,
and point the tool only at specs from sources you control or rely on, just as
you would with any code you choose to execute.

## Tokens and headers

Header values, such as an API token passed with `--header`, are sent to the
target API and are never written to the output. When you paste a report into an
issue, remove or replace any real token, password or internal URL first.
