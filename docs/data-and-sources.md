# Data and sources

## Configured sources and surfaces

- ransomware.live
- Ransomfeed API
- Ransomfeed Web/RQL
- RansomLook
- Ransomnews/Ransomtracker
- VULONE
- ThreatVectr
- BleepingComputer
- Cybernews
- Security Affairs

Breach layer: DataBreaches.net, Have I Been Pwned, California AG, HHS OCR and SEC EDGAR Item 1.05. DDoS layer: DDoSia Monitor.

Every unrestricted lookup tries every configured source. A positive result from one source never stops the others.

## Evidence semantics

The skill keeps these record types apart so that counts stay meaningful: claims, confirmed incidents, OSINT articles, EuRepoC records, wallet observations and aggregate statistics. A leak-site claim is not called a "confirmed attack" unless it is independently confirmed. Dates keep their meaning (incident, publication, filing, reported, submission, catalogue-added).

## Bundled historical datasets

| File                                               | Content (as described in `SKILL.md`)                  |
| -------------------------------------------------- | ----------------------------------------------------- |
| `assets/historical/ransom.json`                    | historical incident and claim records                 |
| `assets/historical/ransom2.json`                   | structured victim, group, country and sector records  |
| `assets/historical/recent.json`                    | claim records with attack and discovery metadata      |
| `assets/historical/wallets.json`                   | ransomware-linked wallet observations with USD fields |
| `assets/historical/eurepoc_global_dataset_1_3.csv` | EuRepoC cyber-incident, legal and attribution dataset |
| `assets/historical/ransomware_repository.csv`      | historical ransomware incident repository             |

These datasets have a coverage boundary. They are not automatically current.

## Origin, coverage and licenses of the historical data

The historical data come from public sources: GitHub collections of historical ransomware data, including chat logs, and the EuRepoC dataset. The sources cited are:

- Zettl-Schabath, K., Bund, J., Müller, M., et al. *Global Dataset of Cyber Incidents*, version 1.3.2. European Repository of Cyber Incidents, Zenodo. DOI [10.5281/zenodo.14965395](https://doi.org/10.5281/zenodo.14965395). Record page: <https://zenodo.org/records/14965395>.
- [mthcht/awesome-lists, folder `Lists`](https://github.com/mthcht/awesome-lists/tree/main/Lists) (GitHub).

| File                                                                                      | Origin                                                                                                                      | What was checked                                                                                |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `eurepoc_global_dataset_1_3.csv`                                                          | EuRepoC Global Dataset of Cyber Incidents, version 1.3. The record page says it covers 2000–2024 and lists 3,416 incidents. | Same MD5 checksum as the file on the Zenodo record. The record states the license CC BY-NC 4.0. |
| `ransom.json`, `ransom2.json`, `recent.json`, `wallets.json`, `ransomware_repository.csv` | Public GitHub collections of historical ransomware data, as stated by the author.                                           | The terms of each source are to be added (see the last section of the README).                  |

### What the license means

- The Apache License of this repository covers its own code and text only.
- CC BY-NC 4.0 asks you to give credit, to link the license and to say if you changed the data. It does not allow commercial use. The bundled EuRepoC file is unchanged.

### Coverage measured with the bundled helper

| Dataset                                               | What `historical_query.py` shows                                                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Claims (`ransom.json`, `ransom2.json`, `recent.json`) | 3,079 claims after de-duplication, for the years 2021–2025                                                               |
| Repository (`ransomware_repository.csv`)              | 946 incident rows, for the years 2013–2021                                                                               |
| EuRepoC (`eurepoc_global_dataset_1_3.csv`)            | 3,414 incident rows in the bundled file                                                                                  |
| Wallets (`wallets.json`)                              | 11,186 wallet records, with balances and transaction amounts in US dollars and a ransomware family label, and no country |

Claims and repository rows count different things, so the skill does not merge them into one series without saying so.
