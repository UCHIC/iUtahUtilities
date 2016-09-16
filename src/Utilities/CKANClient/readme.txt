How to use the iutah_ckan_client python script:

This script provides the following 2 functionalities:

1. update_resource: This function allows to remotely upload a new resource file to a specified dataset at
http://repository.iutahepscor.org and delete any existing resource with the same name as the uploaded resource

Calling Format:
>python iutah_ckan_client.py 'update_resource' 'value for api_key' 'name of the dataset' 'path of file to upload' 'name of the file to replace'

Example:
>python iutah_ckan_client.py 'update_resource' 'db567980cgt8906745678' 'my-original-dataset' 'c:\\odm_site_1_2014.csv' 'odm_site_1_2014.csv'

2. copy_dataset: This function allows to copy a specified dataset (resources within the dataset are not copied) at
http://repository.iutahepscor.org

Auto Generated Dataset Name: copy_ds_[timestamp]

Calling Format:
>python iutah_ckan_client.py 'copy_dataset' 'value for api_key' 'name of the dataset to copy'

Example:
>python iutah_ckan_client.py 'copy_dataset' 'db567980cgt8906745678' 'my-original-dataset'