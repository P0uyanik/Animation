# Character pipeline verification: **PASS**

Blender: 5.3.0. Store version tested: 1.0.0.

| Step | Result |
| --- | --- |
| build from spec | ok |
| geometry fingerprint | ok |
| equals v6 geometry | ok |
| asset store tests | ok |
| reuse test | ok |

v6 geometry: missing [], extra [], count mismatches [], worst numeric difference 0.0 m, exact-hash differences (informational) ['hair_mass']

| Test | Check | Result | Detail |
| --- | --- | --- | --- |
| T7_master_unchanged | master matches manifest before tests | PASS |  |
| T7_master_unchanged | master byte-identical after all tests | PASS | "21d65f461b03fcff" |
| T1_reopen_master | root collection present | PASS |  |
| T1_reopen_master | component collections | PASS | ["accessories", "body", "clothing", "face", "fur", "hair", "landmarks", "rig"] |
| T1_reopen_master | metadata stamped | PASS | {"ps_character_id": "boy_yellow_hoodie", "ps_spec_version": "1.0.0", "ps_build": "charsys/1", "ps_role": "master"} |
| T1_reopen_master | embedded spec matches manifest hash | PASS |  |
| T1_reopen_master | asset marked | PASS |  |
| T1_reopen_master | component body: objects as published | PASS | 4 |
| T1_reopen_master | component face: objects as published | PASS | 13 |
| T1_reopen_master | component hair: objects as published | PASS | 3 |
| T1_reopen_master | component clothing: objects as published | PASS | 27 |
| T1_reopen_master | component accessories: objects as published | PASS | 7 |
| T1_reopen_master | component rig: objects as published | PASS | 1 |
| T1_reopen_master | component landmarks: objects as published | PASS | 7 |
| T1_reopen_master | component fur: objects as published | PASS | 0 |
| T1_reopen_master | rig bones | PASS | [410, 73] |
| T1_reopen_master | every vertex weighted to a deform bone | PASS | 0 |
| T1_reopen_master | expression shape keys | PASS | ["Blink", "BrowDown", "JawOpen", "Smile"] |
| T1_reopen_master | facial controls on rig | PASS | ["face_Blink", "face_BrowDown", "face_JawOpen", "face_Smile"] |
| T1_reopen_master | facial controls deform lids and mouth | PASS | {"lid_mm": 44.2, "mouth_mm": 8.0} |
| T2_pose_master | sleeve follows the arm control | PASS | 0.185 |
| T3_episode_shot | shot files saved outside the store | PASS |  |
| T3_episode_shot | links the store master (not a copy) | PASS | ["//../../../../../../assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend"] |
| T3_episode_shot | no master geometry copied into the shot | PASS | [] |
| T3_episode_shot | pose persisted after reopen | PASS | {"upper_arm_fk.L": [0.9367, 0.0, 0.3502, 0.0], "upper_arm_fk.R": [0.9367, 0.0, -0.3502, 0.0], "head": [0.9781, 0.0, 0.0, 0.2079]} |
| T3_episode_shot | FK switch persisted | PASS | [1.0, 1.0, 1.0, 1.0] |
| T3_episode_shot | facial controls persisted | PASS | {"face_Smile": 1.0, "face_JawOpen": 0.6000000238418579} |
| T3_episode_shot | other shot's expression not present (independent shots) | PASS |  |
| T3_episode_shot | hoodie_sleeve.L deformed by the saved pose/expression after reopen | PASS | 0.0358 |
| T3_episode_shot | mouth deformed by the saved pose/expression after reopen | PASS | 0.0181 |
| T3_episode_shot | renders | PASS | 0.336 |
| T5_isolation | shot A: mesh data is still the linked master data | PASS | {"mesh_library": "//../../../../../../assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend"} |
| T5_isolation | shot B: mesh data is still the linked master data | PASS | {"mesh_library": "//../../../../../../assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend"} |
| T5_isolation | linked vertex in shot equals master value | PASS | {"master_z": 0.696947, "shot_z": 0.696947} |
| T5_isolation | master material unchanged by shot edit | PASS | [0.8, 0.8, 0.8, 1.0] |
| T4_second_episode | links the store master (not a copy) | PASS | ["//../../../../../../assets/characters/boy_yellow_hoodie/versions/1.0.0/boy_yellow_hoodie_master.blend"] |
| T4_second_episode | no master geometry copied into the shot | PASS | [] |
| T4_second_episode | pose persisted after reopen | PASS | {"upper_arm_fk.L": [0.8192, 0.0, -0.5736, 0.0], "thigh_fk.R": [0.9397, -0.342, 0.0, 0.0]} |
| T4_second_episode | FK switch persisted | PASS | [1.0, 1.0, 1.0, 1.0] |
| T4_second_episode | facial controls persisted | PASS | {"face_Blink": 1.0} |
| T4_second_episode | other shot's expression not present (independent shots) | PASS |  |
| T4_second_episode | hoodie_sleeve.L deformed by the saved pose/expression after reopen | PASS | 0.0586 |
| T4_second_episode | lid_upper.L deformed by the saved pose/expression after reopen | PASS | 0.0443 |
| T4_second_episode | renders | PASS | 0.34 |
| T6_gltf_reuse | skeleton | PASS | 73 |
| T6_gltf_reuse | skinned meshes | PASS | 54 |
| T6_gltf_reuse | morph targets | PASS | ["Blink", "BrowDown", "JawOpen", "Smile"] |
| T6_gltf_reuse | imported skin deforms when posed | PASS | 0.185 |
| store | publish 1.0.0 | PASS |  |
| store | verify 1.0.0 | PASS |  |
| store | re-publishing an existing version is refused (immutable) | PASS |  |
| store | bad version string refused | PASS |  |
| store | identity change without owner approval refused | PASS |  |
| store | identity change with recorded owner approval accepted | PASS |  |
| store | manifest records parent and identity change | PASS | {"parent": "1.0.0", "identity_changes": ["proportions"]} |
| store | spec edited after build refused | PASS |  |
| store | approve without --by refused | PASS |  |
| store | approve 1.0.0 | PASS |  |
| store | approved pointer set, history kept | PASS | {"approved": "1.0.0", "reference": "1.0.0"} |
| store | restore approved | PASS |  |
| store | restored files identical to the stored version | PASS |  |
| store | restore into the store refused | PASS |  |
| store | restore into a non-empty folder refused | PASS |  |
| store | tampered master detected by verify | PASS |  |
| store | tampered version cannot be approved | PASS |  |
| store | tampered version cannot be restored | PASS |  |
| store | untouched version still verifies | PASS |  |
