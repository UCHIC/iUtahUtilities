__author__ = 'pabitra'
import sys
import os
import requests
import datetime
from lxml import html
import json


#CKAN_REMOTE_INSTANCE_BASE_URL = 'http://127.0.0.1:5000'
# CKAN_REMOTE_INSTANCE_BASE_URL = 'http://iutah-ckan-test.uwrl.usu.edu'
CKAN_REMOTE_INSTANCE_BASE_URL = 'http://repository.iutahepscor.org'
#CKAN_REMOTE_INSTANCE_BASE_URL = 'http://demo.ckan.org'

def do(f, args=[], kwargs={}):
    while True:
        try:
            x=f(*args, **kwargs)
            return x
        except Exception, e:
            print "EXCEPTION: ", e
            pass

def raise_for_status(response):
    try:
        response.raise_for_status()
    except:
        print "FAILED RFS: %r" % response.content
        raise


def get_parameters(api_key, filepath=None):
    params = {}
    params['CKAN_INSTANCE'] = CKAN_REMOTE_INSTANCE_BASE_URL
    params['CKAN_APIKEY'] = api_key
    if filepath:
        params['FILEPATH'] = filepath
        params['FILENAME'] = os.path.basename(params['FILEPATH'])

    params['NOW'] = datetime.datetime.now().isoformat()
    params['DIRECTORY'] = params['NOW'].replace(":", "").replace("-", "")
    return params

def request_permission():  # phase1
    response = requests.get("{CKAN_INSTANCE}/api/storage/auth/form/{DIRECTORY}/{FILENAME}".format(**params), headers=headers)
    response.raise_for_status()
    j = response.json()
    assert "action" in j
    assert "fields" in j
    print j
    return j


def upload_file(permission):  # phase 2
    response = requests.post("{CKAN_INSTANCE}{action}".format(action=permission['action'], **params),
                             headers=headers,
                             files={'file': (params['FILENAME'], open(params['FILEPATH']))},
                             data={permission['fields'][0]['name']: permission['fields'][0]['value']}
                             )
    response.raise_for_status()
    root = html.fromstring(response.content)
    h1, = root.xpath("//h1/text()")
    assert " Successful" in h1
    url, = root.xpath("//h1/following::a[1]/@href")
    assert params['FILENAME'] in url  # might be issues with URLencoding
    print ("File was uploaded.")
    return url


def create_resource(url, **kwargs):  # phase 3
    data = {"url": url,
            "package_id": params['PACKAGE_ID']}

    newheader = dict(headers)
    newheader['Content-Type'] = "application/x-www-form-urlencoded"  # http://trac.ckan.org/ticket/2942
    data.update(kwargs)
    print data
    response = requests.post("{CKAN_INSTANCE}/api/3/action/resource_create".format(**params),
                             headers=newheader, data=json.dumps(data))

    response.raise_for_status()
    print("Resource was added.")
    #print response.content

#TODO copy the creation of resource_info
def upload(resource_info=None):
    global headers
    headers = {"Authorization": params['CKAN_APIKEY']}
    if resource_info is None:
        print "No resource_info specified, using defaults"
        resource_info = {
            "package_id": params['PACKAGE_ID'],
            "revision_id": params['NOW'],
            "description": "ODM Dataset",
            "format": "CSV",
            # "hash": None,
            "name": params['FILENAME'],
            # "resource_type": None,
            "mimetype": "application/text",
            "mimetype_inner": "text/csv",
            # "webstore_url": None,
            # "cache_url": None,
            # "size": None,
            "created": params['NOW'],
            "last_modified": params['NOW'],
            # "cache_last_updated": None,
            # "webstore_last_updated": None,
            }

    j = do(request_permission)
    url = do(upload_file, [j])
    do(create_resource, [url], resource_info)


def delete_resource(id_of_resource_to_delete):
    headers = {'X-CKAN-API-Key': params['CKAN_APIKEY'], 'Content-Type': 'application/json'}
    data = {'id': id_of_resource_to_delete}
    response = requests.post('{CKAN_INSTANCE}/api/action/resource_delete'.format(**params),
              data=json.dumps(data).encode('ascii'), headers=headers)

    response.raise_for_status()
    print("Resource deleted for replacement.")
    #print (response.content)

def get_package_list(api_key):
    try:
        headers = {'X-CKAN-API-Key': api_key, 'Content-Type': 'application/json'}
        response = requests.post('{CKAN_INSTANCE}/api/action/package_list'.format(CKAN_INSTANCE=CKAN_REMOTE_INSTANCE_BASE_URL), headers=headers)
        response.raise_for_status()
        pkg = json.loads(response.content)['result']
        return pkg
    except Exception as e:
        print "FAILED getting Package list: %r. \n%s" % (response.content, e)
        raise

def _get_package_id_from_name(package_name):
    headers = {'X-CKAN-API-Key': params['CKAN_APIKEY'], 'Content-Type': 'application/json'}
    data = {'id': package_name}
    url = '{CKAN_INSTANCE}/api/action/package_show'.format(**params)
    print url
    print
    response = requests.post('{CKAN_INSTANCE}/api/action/package_show'.format(**params),
              data=json.dumps(data).encode('ascii'), headers=headers)

    response.raise_for_status()

    pkg = json.loads(response.content)['result']

    return pkg['id']

def _get_resource_to_delete(resource_file_name_to_delete):
    headers = {'X-CKAN-API-Key': params['CKAN_APIKEY'], 'Content-Type': 'application/json'}
    data = {'id': params['PACKAGE_ID']}
    response = requests.post('{CKAN_INSTANCE}/api/action/package_show'.format(**params),
              data=json.dumps(data).encode('ascii'), headers=headers)

    response.raise_for_status()

    pkg_resources = json.loads(response.content)['result']['resources']

    res_to_delete = None
    try:
        for res in pkg_resources:
            print res['url']
            file_name = res['url'].split('/')[-1]
            if file_name.replace("_", "-").lower() == resource_file_name_to_delete.replace("_", "-").lower():
                res_to_delete = res
                return res_to_delete
    except Exception as e:
        print "caught an exception "+ e

    return res_to_delete


def insert_resource(api_key=None, package_name=None, file_to_upload=None, resource_info=None):
    """
    created by Stephanie Reede: 12-7-15
    """
    global params
    global headers

    if not api_key:
        if len(sys.argv) < 5:
            raise RuntimeError("Invalid number of arguments. Needs at least 4 arguments ('insert_resource', "
                               "api_key, package_name, file_to_upload).")
        else:
            api_key = sys.argv[2]

    if not package_name:
        if len(sys.argv) < 5:
            raise RuntimeError("Invalid number of arguments. Needs at least 4 arguments ('insert_resource', "
                               "api_key, package_name, file_to_upload). ")
        else:
            package_name = sys.argv[3]

    if not file_to_upload:
        if len(sys.argv) < 5:
            raise RuntimeError("Invalid number of arguments. Needs at least 4 arguments ('insert_resource', "
                               "api_key, package_name, file_to_upload). ")
        else:
            file_to_upload = sys.argv[4]

    if not os.path.isfile(file_to_upload):
        raise RuntimeError("File to upload is not found.")

    if not resource_info:
        if len(sys.argv) == 6:
            try:
                # convert json string to python dict
                resource_info = json.loads(sys.argv[5])
            except:
                raise RuntimeError("Value for the parameter 'resource_info' should be a json string.")

    params = get_parameters(api_key=api_key, filepath=file_to_upload)
    #params['PACKAGE_ID'] = package_id
    params['PACKAGE_NAME'] = package_name

    # get id of the package from package name
    params['PACKAGE_ID'] = _get_package_id_from_name(package_name)

    if not resource_info:
        resource_info = {
                "package_id": params['PACKAGE_ID'],
                "revision_id": params['NOW'],
                "description": "New file upload",
                "format": "CSV",
                # "hash": None,
                "name": params['FILENAME'],
                # "resource_type": None,
                "mimetype": "application/text",
                "mimetype_inner": "text/csv",
                # "webstore_url": None,
                # "cache_url": None,
                # "size": None,
                "created": params['NOW'],
                "last_modified": params['NOW'],
                # "cache_last_updated": None,
                # "webstore_last_updated": None,
                }

    upload(resource_info)
    print("Resource created successfully."+ params['PACKAGE_NAME'] )


def update_resource(api_key=None, package_name=None, file_to_upload=None, replace_file_name=None, resource_info=None):
    global params
    global headers

    if not api_key:
        if len(sys.argv) < 6:
            raise RuntimeError("Invalid number of arguments. Needs at least 5 arguments ('update_resource', "
                               "api_key, package_name, file_to_upload, replace_file_name).")
        else:
            api_key = sys.argv[2]

    if not package_name:
        if len(sys.argv) < 6:
            raise RuntimeError("Invalid number of arguments. Needs at least 5 arguments ('update_resource', "
                               "api_key, package_name, file_to_upload, replace_file_name).")
        else:
            package_name = sys.argv[3]

    if not file_to_upload:
        if len(sys.argv) < 6:
            raise RuntimeError("Invalid number of arguments. Needs at least 5 arguments ('update_resource', "
                               "api_key, package_name, file_to_upload, replace_file_name).")
        else:
            file_to_upload = sys.argv[4]

    if not os.path.isfile(file_to_upload):
        raise RuntimeError("File to upload is not found.")

    if not replace_file_name:
        if len(sys.argv) < 6:
            raise RuntimeError("Invalid number of arguments. Needs at least 5 arguments ('update_resource', "
                               "api_key, package_name, file_to_upload, replace_file_name).")
        else:
            replace_file_name = sys.argv[5].lower()
    else:
        replace_file_name = replace_file_name.lower()

    if not resource_info:
        if len(sys.argv) == 7:
            try:
                # convert json string to python dict
                resource_info = json.loads(sys.argv[6])
            except:
                raise RuntimeError("Value for the parameter 'resource_info' should be a json string.")

    params = get_parameters(api_key=api_key, filepath=file_to_upload)
    #params['PACKAGE_ID'] = package_id
    params['PACKAGE_NAME'] = package_name

    # get id of the package from package name
    params['PACKAGE_ID'] = _get_package_id_from_name(package_name)

    # since the upload file name can be same as the name of the file to be replaced
    # get the id of the file that will be deleted before uploading a new file
    res_to_delete = _get_resource_to_delete(replace_file_name)
    id_of_file_to_delete = None

    if res_to_delete:
        id_of_file_to_delete = res_to_delete['id']
        if not resource_info:
            resource_info = {
                    "package_id": params['PACKAGE_ID'],
                    "revision_id": params['NOW'],
                    "description": res_to_delete['description'],
                    "format": "CSV",
                    # "hash": None,
                    "name": params['FILENAME'],
                    # "resource_type": None,
                    "mimetype": "application/text",
                    "mimetype_inner": "text/csv",
                    # "webstore_url": None,
                    # "cache_url": None,
                    # "size": None,
                    "created": params['NOW'],
                    "last_modified": params['NOW'],
                    # "cache_last_updated": None,
                    # "webstore_last_updated": None,
                    }

    upload(resource_info)

    if id_of_file_to_delete:
        delete_resource(id_of_file_to_delete)
    else:
        print("No matching file was found to delete.")


def copy_dataset(api_key=None, package_name=None):

    if not api_key:
        if len(sys.argv) < 3:
            raise RuntimeError("Invalid number of arguments. Needs 3 arguments ('copy_dataset', api_key, package_name).")
        else:
            api_key = sys.argv[2]

    if not package_name:
        if len(sys.argv) < 4:
            raise RuntimeError("Invalid number of arguments. Needs 3 arguments ('copy_dataset', api_key, package_name).")
        else:
            package_name = sys.argv[3]

    params = get_parameters(api_key=api_key)
    headers = {'X-CKAN-API-Key': params['CKAN_APIKEY'], 'Content-Type': 'application/json'}
    data = {'id': package_name}

    response = requests.post('{CKAN_INSTANCE}/api/action/package_show'.format(**params),
              data=json.dumps(data).encode('ascii'), headers=headers)

    response.raise_for_status()

    pkg_dict = json.loads(response.content)['result']

    tag_string = ','.join(tag['name'] for tag in pkg_dict['tags'])
    tags = []

    for tag in pkg_dict['tags']:
        tags.append({'state': 'active', 'name': tag['name']})

    dataset_name = 'copy_ds_' + params['NOW'].replace(":", "_").replace("-", "_").replace(".", "_").replace('T', "")
    data = {'name': dataset_name,
            'author': pkg_dict['author'],
            'author_email': pkg_dict['author_email'],
            'maintainer': pkg_dict['maintainer'],
            'maintainer_email': pkg_dict['maintainer_email'],
            'notes': pkg_dict['notes'],
            'license_id': pkg_dict['license_id'],
            'url': pkg_dict['url'],
            'state': pkg_dict['state'],
            'version': pkg_dict['version'],
            'type': pkg_dict['type'],
            'resources': [],
            'tag_string': tag_string,
            'tags': tags,
            'groups': pkg_dict['groups'],
            'owner_org': pkg_dict['owner_org'],
            'private': pkg_dict['private'],
            'creators': pkg_dict['creators'],
            'contributors': pkg_dict['contributors'],
            'variable_description': pkg_dict['variable_description'],
            'variables': pkg_dict['variables'],
            'access_information': pkg_dict['access_information'],
            'citation': pkg_dict['citation'],   # citation will not be copied, copied dataset needs to be manually updated to get the citation
            'data_collection_method': pkg_dict['data_collection_method'],
            'data_processing_method': pkg_dict['data_processing_method'],
            'data_type': pkg_dict['data_type'],
            'east_extent': pkg_dict['east_extent'],
            'south_extent': pkg_dict['south_extent'],
            'west_extent': pkg_dict['west_extent'],
            'north_extent': pkg_dict['north_extent'],
            'feature_types': pkg_dict['feature_types'],
            'horz_coord_system': pkg_dict['horz_coord_system'],
            'vert_coord_system': pkg_dict['vert_coord_system'],
            'language': pkg_dict['language'],
            'purpose': pkg_dict['purpose'],
            'required_software': pkg_dict['required_software'],
            'research_focus': pkg_dict['research_focus'],
            'spatial': pkg_dict['spatial'],
            'status': pkg_dict['status'],
            'study_area': pkg_dict['study_area'],
            'sub_name': pkg_dict['sub_name'],
            'sub_email': pkg_dict['sub_email'],
            'temporal': pkg_dict['temporal'],
            'update_frequency': pkg_dict['update_frequency']
            }

    headers = {'X-CKAN-API-Key': params['CKAN_APIKEY'], 'Content-Type': 'application/json'}

    response = requests.post("{CKAN_INSTANCE}/api/3/action/package_create".format(**params),
                             headers=headers, data=json.dumps(data))

    response.raise_for_status()


    print("Dataset copied successfully.")
    #print (response.content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise RuntimeError("Invalid number of arguments. There needs to be at least one argument specifying the "
                           "function to execute (allowed functions are: update_resource, copy_dataset, insert_resource).")
    if sys.argv[1] == 'update_resource':
        update_resource()
    elif sys.argv[1] == 'copy_dataset':
        copy_dataset()
    elif sys.argv[1] == 'insert_resource':
        insert_resource()
    else:
        print "%s not found" % sys.argv[1]
        #raise RuntimeError("Invalid function name (%s) to execute "
                           # "(allowed functions are: update_resource, copy_dataset, insert_resource)." % sys.argv[1])