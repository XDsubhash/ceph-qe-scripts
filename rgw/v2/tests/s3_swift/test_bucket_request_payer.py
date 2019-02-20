# test basic creation of buckets with objects
import os, sys

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../..")))
from v2.lib.resource_op import Config
import v2.lib.resource_op as s3lib
from v2.lib.s3.auth import Auth
import v2.utils.log as log
import v2.utils.utils as utils
import traceback
import argparse
from v2.lib.exceptions import TestExecError
from v2.utils.test_desc import AddTestInfo
from v2.lib.s3.write_io_info import IOInfoInitialize, BasicIOInfoStructure
import resuables
from v2.utils.utils import HttpResponseParser
import yaml

TEST_DATA_PATH = None


def test_exec(config, requester):
    test_info = AddTestInfo('Bucket Request Payer')
    io_info_initialize = IOInfoInitialize()
    basic_io_structure = BasicIOInfoStructure()
    io_info_initialize.initialize(basic_io_structure.initial())
    log.info('requester type: %s' % requester)

    try:
        test_info.started_info()
        # create user
        all_users_info = s3lib.create_users(config.user_count)
        for each_user in all_users_info:
            # authenticate
            auth = Auth(each_user)
            rgw_conn = auth.do_auth()
            # create buckets
            log.info('no of buckets to create: %s' % config.bucket_count)
            for bc in range(config.bucket_count):
                bucket_name_to_create = utils.gen_bucket_name_from_userid(each_user['user_id'], rand_no=bc)
                log.info('creating bucket with name: %s' % bucket_name_to_create)
                # bucket = s3_ops.resource_op(rgw_conn, 'Bucket', bucket_name_to_create)
                bucket = resuables.create_bucket(bucket_name=bucket_name_to_create, rgw=rgw_conn, user_info=each_user)
                bucket_request_payer = s3lib.resource_op({'obj': rgw_conn,
                                                          'resource': 'BucketRequestPayment',
                                                          'args': [bucket.name]
                                                          })
                # change the bucket request payer to 'requester'
                payer = {'Payer': requester}
                response = s3lib.resource_op({'obj': bucket_request_payer,
                                              'resource': 'put',
                                              'kwargs': dict(RequestPaymentConfiguration=payer)})
                log.info(response)
                if response is not None:
                    response = HttpResponseParser(response)
                    if response.status_code == 200:
                        log.info('bucket created')
                    else:
                        raise TestExecError("bucket request payer modification failed")
                else:
                    raise TestExecError("bucket request payer modification failed")
                payer = bucket_request_payer.payer
                log.info('bucket request payer: %s' % payer)
                if payer != 'Requester':
                    TestExecError('Request payer is not set or changed properly ')
                log.info('s3 objects to create: %s' % config.objects_count)
                if config.objects_count is not None:
                    for oc, size in config.mapped_sizes.items():
                        config.obj_size = size
                        s3_object_name = utils.gen_s3_object_name(bucket.name, oc)
                        resuables.upload_object(s3_object_name, bucket, TEST_DATA_PATH, config, each_user)
        test_info.success_status('test passed')
        sys.exit(0)

    except Exception, e:
        log.info(e)
        log.info(traceback.format_exc())
        test_info.failed_status('test failed')
        sys.exit(1)

    except TestExecError, e:
        log.info(e)
        log.info(traceback.format_exc())
        test_info.failed_status('test failed')
        sys.exit(1)


if __name__ == '__main__':
    project_dir = os.path.abspath(os.path.join(__file__, "../../.."))
    test_data_dir = 'test_data'
    TEST_DATA_PATH = (os.path.join(project_dir, test_data_dir))
    log.info('TEST_DATA_PATH: %s' % TEST_DATA_PATH)
    if not os.path.exists(TEST_DATA_PATH):
        log.info('test data dir not exists, creating.. ')
        os.makedirs(TEST_DATA_PATH)
    parser = argparse.ArgumentParser(description='RGW S3 Automation')
    parser.add_argument('-c', dest="config",
                        help='RGW Test yaml configuration', default=None)
    args = parser.parse_args()
    yaml_file = args.config
    config = Config(yaml_file)
    config.read()
    if (config.mapped_sizes is None) and (config.objects_count is not None):
        config.mapped_sizes = utils.make_mapped_sizes(config)
    requester = 'Requester'
    test_exec(config, requester)
    requester = 'Owner'
    test_exec(config, requester)
