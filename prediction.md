# Prediction

We plan to use two levels of detections:

1- one to predict the location of the scenses in the mansucript pages
2- one to predict location and classification of the descriptors in each of the scenes

## Prediction of location of Mandragore Scenes

We expect to use dh_segment, with post processing Ornaments

### Tools vailable for Ornament predictions

* root folder for programs: `exps/Ornaments`
* programs:
  * `ornaments_data_set_generator.py -i image-folder -o data-folder` : generate a classes.txt for the training/prediction with one class and one color (0,255,0). And copy files from image-folder + labels into data-folder, spreading into 3 differents sets (train, test or validation). Input-folder is pointing the images folder. However it expects that the directory is sibling to a 'labels' directory that contains labels. I mean a 2 color png image.
  => check DEMO to see how to generate these labels from known localization of scense in (x,y,w,h)
  **expected to by used with the `train.py` program (or for evaluation score after post-processing ?)**

  * `ornaments_process_sets.py -m <model-dir> -i <input-data-folder> -o <output-prediction-dir> -pp [flag for post-process-only]`
    * `<model-dir>` should be either loc of sownloaded model, or nodel trained thanks to TRAIN.py on the set generated above
    * `<input-data-folder>` should be the set of images we want the detection for. if not option `-pp` the program will launch a prediction on the set of images, before running the post-process for ornaments
    * `<output-prediction-dir>` the output for predictions (will contain at least XML docs of the predictions)
  
    * Some option allows to change the parameters of post-processing only : `--post_process_params <json-file>` wher json file contains a section `params` with the values for post-precessing.

      * Default values are: `{"threshold": -1, "ksize_open": [5, 5], "ksize_close": [5, 5]}`

  * `ornaments_process_eval.py -gt <input-data-folder> -d <npy-prediction-dir> -o <output-eval-dir> -p <param-file>`. Compute the scores of prediction against each of the params of the param file (default is provided if param file is not)

## dh_segment models and predictions

TO BE DESCRIBED

* reenforcement on existing models (vgg16 and resnet50)
* use post processing to extract segments from the prediction on the image
* several cases : lines, polylines, boxes
* ornaments is using a box detection - I guess on the "white parts of the image, that is not outside - not the background)
