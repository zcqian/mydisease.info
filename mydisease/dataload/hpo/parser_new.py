from collections import defaultdict
from biothings.utils.dataload import dict_sweep, unlist
import pandas as pd
import json

from . import file_path_disease_hpo, file_path_mondo


# Build a dictionary to map from UMLS identifier to MONDO ID
def construct_orphanet_omim_to_mondo_library(file_path_mondo):
    umls_2_mondo = defaultdict(list)
    with open(file_path_mondo) as f:
        data = json.loads(f.read())
        mondo_docs = data['graphs'][0]['nodes']
        for record in mondo_docs:
            if 'id' in record and record['id'].startswith('http://purl.obolibrary.org/obo/MONDO_'):
                if 'meta' in record and 'xrefs' in record['meta']:
                    for _xref in record['meta']['xrefs']:
                        prefix = _xref['val'].split(':')[0]
                        if prefix.lower() == 'orphanet' or prefix.lower() == 'omim':
                            mondo_id = 'MONDO:' + record['id'].split('_')[-1]
                            umls_2_mondo[_xref['val'].upper()].append(mondo_id)
    return umls_2_mondo


def process_disease2hp(file_path_disease_hpo):
    df_disease_hpo = pd.read_csv(file_path_disease_hpo, sep="\t")
    df_disease_hpo = df_disease_hpo.rename(index=str, columns={"DB_Name": "disease_name", "HPO_ID": "hpo"})
    df_disease_hpo['#DB'].replace('ORPHA', 'ORPHANET',inplace=True)
    df_disease_hpo['disease_id'] = df_disease_hpo.apply(lambda row: row["#DB"] + ":" + str(row["DB_Object_ID"]), axis=1)
    df_disease_hpo = df_disease_hpo.where((pd.notnull(df_disease_hpo)), None)
    d = []
    for did, subdf in df_disease_hpo.groupby('disease_id'):
        records = subdf.to_dict(orient='records')
        pathway_related = []
        for record in records:
            record_dict = {}
            for k, v in record.items():
                # name the field based on pathway database
                if k == 'sex':
                    record_dict[k.lower()] = v.lower()
                elif k not in {'Date_Created', '#DB', 'DB_Object_ID', 'DB_Reference', 'disease_id'}:
                    record_dict[k.lower()] = v
            pathway_related.append(record_dict)
        drecord = {'_id': did, 'hpo': pathway_related}
        d.append(drecord)
    return {x['_id']: x['hpo'] for x in d}


def calculate_mondo_mismatch():
    d_hpo = process_disease2hp(file_path_disease_hpo)
    orphanet_omim_2_mondo = construct_orphanet_omim_to_mondo_library(file_path_mondo)
    matched = []
    mismatched = []
    for disease_id in d_hpo.keys():
        if disease_id in orphanet_omim_2_mondo:
            matched.append(disease_id)
        else:
            mismatched.append(disease_id)
    return {'matched': matched, 'mismatch': mismatched}

def load_data():
    d_hpo = process_disease2hp(file_path_disease_hpo)
    orphanet_omim_2_mondo = construct_orphanet_omim_to_mondo_library(file_path_mondo)
    for disease_id in d_hpo.keys():
    #for disease_id in set(list(d_go_bp.keys()) + list(d_go_mf.keys()) + list(d_go_cc.keys()) + list(d_pathway.keys())):
        if disease_id in orphanet_omim_2_mondo:
            mondo_id = orphanet_omim_2_mondo[disease_id]
            for _mondo in mondo_id:
                if disease_id.startswith('OMIM'):
                    _doc = {'_id': _mondo,
                            'hpo': {
                                'omim': disease_id.split(':')[1],
                                'phenotype_related_to_disease': d_hpo.get(disease_id, {})
                                }
                           }
                elif disease_id.startswith('ORPHANET'):
                    _doc = {'_id': _mondo,
                            'hpo': {
                                'orphanet': disease_id.split(':')[1],
                                'phenotype_related_to_disease': d_hpo.get(disease_id, {})
                                }
                           }
                else:
                    print(disease_id)
                _doc = (dict_sweep(unlist(_doc), [None]))
                yield _doc

        else:
            if disease_id.startswith('OMIM'):
                _doc = {'_id': disease_id,
                        'hpo': {
                            'omim': disease_id.split(':')[1],
                            'phenotype_related_to_disease': d_hpo.get(disease_id, {})
                            }
                        }
            elif disease_id.startswith('ORPHANET'):
                _doc = {'_id': disease_id,
                        'hpo': {
                            'orphanet': disease_id.split(':')[1],
                            'phenotype_related_to_disease': d_hpo.get(disease_id, {})
                            }
                        }
            else:
                _doc = {'_id': disease_id,
                        'hpo': {
                            'decipher': disease_id.split(':')[1],
                            'phenotype_related_to_disease': d_hpo.get(disease_id, {})
                            }
                        }
            _doc = (dict_sweep(unlist(_doc), [None]))
            yield _doc
