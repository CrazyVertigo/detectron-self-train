"""Perform inference on one or more datasets."""

import argparse
import cv2
import os
import pprint
import sys
import time

import torch

import _init_paths  # pylint: disable=unused-import
from core.config import cfg, merge_cfg_from_file, merge_cfg_from_list, assert_and_infer_cfg
from core.test_engine import run_inference
import utils.logging

# OpenCL may be enabled by default in OpenCV3; disable it because it's not
# thread safe and causes unwanted GPU memory allocations.
cv2.ocl.setUseOpenCL(False)


def parse_args():
    """Parse in command line arguments"""
    parser = argparse.ArgumentParser(description='Test a Fast R-CNN network')
    parser.add_argument(
        '--dataset',
        help='training dataset')
    parser.add_argument(
        '--cfg', dest='cfg_file', required=True,
        help='optional config file')

    parser.add_argument(
        '--load_ckpt', help='path of checkpoint to load')
    parser.add_argument(
        '--load_detectron', help='path to the detectron weight pickle file')

    parser.add_argument(
        '--output_dir',
        help='output directory to save the testing results. If not provided, '
             'defaults to [args.load_ckpt|args.load_detectron]/../test.')

    parser.add_argument(
        '--set', dest='set_cfgs',
        help='set config keys, will overwrite config in the cfg_file.'
             ' See lib/core/config.py for all options',
        default=[], nargs='*')

    parser.add_argument(
        '--range',
        help='start (inclusive) and end (exclusive) indices',
        type=int, nargs=2)
    parser.add_argument(
        '--multi-gpu-testing', help='using multiple gpus for inference',
        action='store_true')
    parser.add_argument(
        '--vis', dest='vis', help='visualize detections', action='store_true')

    return parser.parse_args()


if __name__ == '__main__':

    if not torch.cuda.is_available():
        sys.exit("Need a CUDA device to run the code.")

    logger = utils.logging.setup_logging(__name__)
    args = parse_args()
    logger.info('Called with args:')
    logger.info(args)
    

    assert (torch.cuda.device_count() == 1) ^ bool(args.multi_gpu_testing)

    assert bool(args.load_ckpt) ^ bool(args.load_detectron), \
        'Exactly one of --load_ckpt and --load_detectron should be specified.'
    if args.output_dir is None:
        ckpt_path = args.load_ckpt if args.load_ckpt else args.load_detectron
        args.output_dir = os.path.join(
            os.path.dirname(os.path.dirname(ckpt_path)), 'test')
        logger.info('Automatically set output directory to %s', args.output_dir)
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    cfg.VIS = args.vis
    
    if args.cfg_file is not None:
        merge_cfg_from_file(args.cfg_file)
    if args.set_cfgs is not None:
        merge_cfg_from_list(args.set_cfgs)

    if args.dataset == "coco2017":
        cfg.TEST.DATASETS = ('coco_2017_val',)
        cfg.MODEL.NUM_CLASSES = 81
    
    # Specify VAL datasets
    # CS6 easy val set
    elif args.dataset == 'cs6_annot_eval_val-easy':
        cfg.TEST.DATASETS = ('cs6_annot_eval_val-easy',)
        cfg.MODEL.NUM_CLASSES = 2
    # CS6 Test set
    elif args.dataset == 'cs6_test_gt':
        cfg.TEST.DATASETS = ('cs6_TEST_gt',)
        cfg.MODEL.NUM_CLASSES = 2

    # Cityscapes peds
    elif args.dataset == 'cityscapes_val':
        cfg.TEST.DATASETS = ('cityscapes_val',)
        cfg.MODEL.NUM_CLASSES = 2  # Cityscapes cars
    elif args.dataset == 'cityscapes_car_val':
        cfg.TEST.DATASETS = ('cityscapes_car_val',)
        cfg.MODEL.NUM_CLASSES = 2


    # BDD sets -- with constraints
    elif args.dataset == 'bdd_any_any_daytime':
        cfg.TEST.DATASETS = ('bdd_any_any_daytime_val',) # or whichever constraint dataset to be used (scene, weather, etc.)
        cfg.MODEL.NUM_CLASSES = 2
    elif args.dataset == 'bdd_clear_any_daytime':
        cfg.TEST.DATASETS = ('bdd_clear_any_daytime_val',)
        cfg.MODEL.NUM_CLASSES = 2
    elif args.dataset == 'bdd_any_any_any':
        cfg.TEST.DATASETS = ('bdd_any_any_any_val',)
        cfg.MODEL.NUM_CLASSES = 2

    # Cityscapes pedestrians
    elif args.dataset == 'cityscapes_peds_val':
        cfg.TEST_DATASETS = ('cityscapes_peds_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # BDD pedestrians
    elif args.dataset == 'bdd_peds_val':
        cfg.TEST.DATASETS = ('bdd_peds_val',) # val set for bdd peds: clear_any_daytime
        cfg.MODEL.NUM_CLASSES = 2
    elif args.dataset == 'bdd_peds_full_val':
        cfg.TEST.DATASETS = ('bdd_peds_full_val',) # val set for full bdd peds: any_any_any
        cfg.MODEL.NUM_CLASSES = 2
    elif args.dataset == 'bdd_peds_not_clear_any_daytime_val':
        cfg.TEST.DATASETS = ('bdd_peds_not_clear_any_daytime_val',) # val set for complement of clear_any_daytime
        cfg.MODEL.NUM_CLASSES = 2
    elif args.dataset == 'bdd_peds_dets18k_target_domain':
        cfg.TEST.DATASETS = ('bdd_peds_dets18k_target_domain',) # bbd dets json: for bdd data dist experiment
        cfg.MODEL.NUM_CLASSES = 2
    # BDD pedestrians test set
    elif args.dataset == 'bdd_peds_TEST':
        cfg.TEST.DATASETS = ('bdd_peds_TEST',)
        cfg.MODEL.NUM_CLASSES = 2
    
    # BDD sub-domains
    # night
    elif args.dataset == 'bdd_peds_any_any_night_val':
        cfg.TEST.DATASETS = ('bdd_peds_any_any_night_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # rainy, day
    elif args.dataset == 'bdd_peds_rainy_any_daytime_val':
        cfg.TEST.DATASETS = ('bdd_peds_rainy_any_daytime_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # rainy night
    elif args.dataset == 'bdd_peds_rainy_any_night_val':
        cfg.TEST.DATASETS = ('bdd_peds_rainy_any_night_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # overcast, day
    elif args.dataset == 'bdd_peds_overcast_any_daytime_val':
        cfg.TEST.DATASETS = ('bdd_peds_overcast_any_daytime_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # overcast, night
    elif args.dataset == 'bdd_peds_overcast_any_night_val':
        cfg.TEST.DATASETS = ('bdd_peds_overcast_any_night_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # snowy, day
    elif args.dataset == 'bdd_peds_snowy_any_daytime_val':
        cfg.TEST.DATASETS = ('bdd_peds_snowy_any_daytime_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # snowy, night
    elif args.dataset == 'bdd_peds_snowy_any_night_val':
        cfg.TEST.DATASETS = ('bdd_peds_snowy_any_night_val',)
        cfg.MODEL.NUM_CLASSES = 2
    
    # overcast, rainy day
    elif args.dataset == 'bdd_peds_overcast,rainy_any_daytime_val':
        cfg.TEST.DATASETS = ('bdd_peds_overcast,rainy_any_daytime_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # overcast, rainy night
    elif args.dataset == 'bdd_peds_overcast,rainy_any_night_val':
        cfg.TEST.DATASETS = ('bdd_peds_overcast,rainy_any_night_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # overcast, rainy, snowy day
    elif args.dataset == 'bdd_peds_overcast,rainy,snowy_any_daytime_val':
        cfg.TEST.DATASETS = ('bdd_peds_overcast,rainy,snowy_any_daytime_val',)
        cfg.MODEL.NUM_CLASSES = 2
    # overcast, rainy, snowy day
    elif args.dataset == 'bdd_peds_overcast,rainy,snowy_any_night_val':
        cfg.TEST.DATASETS = ('bdd_peds_overcast,rainy,snowy_any_night_val',)
        cfg.MODEL.NUM_CLASSES = 2
    ##### end of BDD sub-domains #####
    
    # WIDER val
    elif args.dataset == 'wider_val':
        cfg.TEST.DATASETS = ('wider_val',)
        cfg.MODEL.NUM_CLASSES = 2


    elif args.dataset == "keypoints_coco2017":
        cfg.TEST.DATASETS = ('keypoints_coco_2017_val',)
        cfg.MODEL.NUM_CLASSES = 2

    else:  # For subprocess call
        assert cfg.TEST.DATASETS, 'cfg.TEST.DATASETS shouldn\'t be empty'
    assert_and_infer_cfg()

    logger.info('Testing with config:')
    logger.info(pprint.pformat(cfg))

    # For test_engine.multi_gpu_test_net_on_dataset
    args.test_net_file, _ = os.path.splitext(__file__)
    # manually set args.cuda
    args.cuda = True

    run_inference(
        args,
        ind_range=args.range,
        multi_gpu_testing=args.multi_gpu_testing,
        check_expected_results=True)
