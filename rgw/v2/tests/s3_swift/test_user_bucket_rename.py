# test user and bucket rename with tenanted and non tenanted users
import os, sys

sys.path.append(os.path.abspath(os.path.join(__file__, "../../../..")))
from v2.lib.resource_op import Config
import v2.utils.log as log
import v2.utils.utils as utils
import traceback
import argparse
import yaml
import json
from v2.lib.exceptions import TestExecError
from v2.utils.test_desc import AddTestInfo
from v2.lib.s3.write_io_info import IOInfoInitialize, BasicIOInfoStructure
from v2.lib.s3.write_io_info import AddUserInfo, BucketIoInfo
from v2.lib.read_io_info import ReadIOInfo
from v2.lib.s3.auth import Auth
from v2.tests.s3_swift import resuables
import v2.lib.resource_op as s3lib
import v2.lib.manage_data as manage_data

TEST_DATA_PATH = None


# create tenanted and non tenanted user
# create buckets for both users
# rename buckets and users

def test_exec(config):
    test_info = AddTestInfo('test swift user key gen')
    io_info_initialize = IOInfoInitialize()
    basic_io_structure = BasicIOInfoStructure()
    io_info_initialize.initialize(basic_io_structure.initial())

    try:
        test_info.started_info()
        non_ten_buckets = {}
        ten_buckets = {}
        user_names = ['bill', 'newbill', 'joe', 'newjoe']
        tenant1 = 'tenant'
        non_ten_users = s3lib.create_users(config.user_count)
        ten_users = s3lib.create_tenant_users(config.user_count, tenant1)
        # Rename users
        if config.test_ops['rename_users'] is True:
            for user in non_ten_users:
                new_non_ten_name = 'new' + user['user_id']
                out = resuables.rename_user(user['user_id'], new_non_ten_name)
                if out is False:
                    raise TestExecError("RGW User rename error")
                log.info('output :%s' % out)
                user['user_id'] = new_non_ten_name

            for ten_user in ten_users:
                new_ten_name = 'new' + ten_user['user_id']
                out1 = resuables.rename_user(ten_user['user_id'], new_ten_name, tenant1)
                if out1 is False:
                    raise TestExecError("RGW User rename error")
                log.info('output :%s' % out1)
                ten_user['user_id'] = new_ten_name
        # create buckets and test rename
        for user in non_ten_users:
            auth = Auth(user, ssl=config.ssl)
            rgw_conn = auth.do_auth()
            bucket_name_to_create1 = utils.gen_bucket_name_from_userid(user['user_id'])
            log.info('creating bucket with name: %s' % bucket_name_to_create1)
            bucket = resuables.create_bucket(bucket_name_to_create1, rgw_conn, user)
            non_ten_buckets[user['user_id']] = bucket_name_to_create1
            if config.test_ops['rename_buckets'] is True:
                bucket_new_name1 = 'new' + bucket_name_to_create1
                non_ten_buckets[user['user_id']] = bucket_new_name1
                out2 = resuables.rename_bucket(bucket.name, bucket_new_name1, user['user_id'])
                if out2 is False:
                    raise TestExecError("RGW Bucket rename error")
                log.info('output :%s' % out2)

        for ten_user in ten_users:
            auth = Auth(ten_user, ssl=config.ssl)
            rgw_conn = auth.do_auth()
            bucket_name_to_create2 = utils.gen_bucket_name_from_userid(ten_user['user_id'])
            log.info('creating bucket with name: %s' % bucket_name_to_create2)
            bucket = resuables.create_bucket(bucket_name_to_create2, rgw_conn, ten_user)
            ten_buckets[ten_user['user_id']] = bucket_name_to_create2
            if config.test_ops['rename_buckets'] is True:
                bucket_new_name2 = 'new' + bucket_name_to_create2
                ten_buckets[ten_user['user_id']] = bucket_new_name2
                out3 = resuables.rename_bucket(bucket.name, bucket_new_name2, ten_user['user_id'], tenant1)
                if out3 is False:
                    raise TestExecError("RGW Bucket rename error")
                log.info('output :%s' % out3)
        if config.test_ops['bucket_link_unlink'] is True:
            # Bucket unlink and link from non tenanted to tenanted users
            out4 = resuables.unlink_bucket(non_ten_users[0]['user_id'], non_ten_buckets[non_ten_users[0]['user_id']])
            if out4 is False:
                raise TestExecError("RGW Bucket unlink error")
            log.info('output :%s' % out4)
            resuables.link_chown_to_tenanted(ten_users[0]['user_id'], non_ten_buckets[non_ten_users[0]['user_id']], tenant1)

            # Bucket unlink and link from tenanted to non tenanted users
            out5 = resuables.unlink_bucket(ten_users[0]['user_id'], ten_buckets[ten_users[0]['user_id']], tenant1)
            if out5 is False:
                raise TestExecError("RGW Bucket unlink error")
            log.info('output :%s' % out5)
            resuables.link_chown_to_nontenanted(non_ten_users[0]['user_id'], ten_buckets[ten_users[0]['user_id']], tenant1)

        test_info.success_status('test passed')
        sys.exit(0)

    except Exception as e:
        log.info(e)
        log.info(traceback.format_exc())
        test_info.failed_status('test failed')
        sys.exit(1)

    except TestExecError as e:
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
                        help='RGW Test yaml configuration')
    args = parser.parse_args()
    yaml_file = args.config
    config = Config(yaml_file)
    config.read()
    test_exec(config)

    # todo: Verify code to be executed after rename lib changes
    # Verify data
    # read_io = ReadIOInfo()
    # read_io.verify_io()
