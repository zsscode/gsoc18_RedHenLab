import time
import os
import os.path
import numpy as np
import sys
import pdb
import csv
import cv2
from random import shuffle


# USE CPU ONLY
# import os
# os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"   # see issue #152
# os.environ["CUDA_VISIBLE_DEVICES"] = ""



from keras.callbacks import TensorBoard, ModelCheckpoint, EarlyStopping, CSVLogger
from keras.utils import to_categorical
from keras.preprocessing import image
from keras.applications.vgg16 import preprocess_input
from sklearn.metrics import classification_report, confusion_matrix
from keras.models import load_model, Model
import tensorflow as tf

config = tf.ConfigProto()
config.gpu_options.allow_growth=True
sess = tf.Session(config=config)
np.set_printoptions(threshold=np.inf)







import gazefollow_keras_befOverfittingTests



OUTPUT_GRID_SIZE = 5
INTERMEDIATE_GRID_SIZE = 14


INPUT_IMAGE_SHAPE = (224, 224, 3)
HEAD_IMAGE_SHAPE = (224, 224, 3)
HEAD_LOCATION_SHAPE = (INTERMEDIATE_GRID_SIZE*INTERMEDIATE_GRID_SIZE,1,1)


def PV(arr):
    for x in arr:
        print (x);

def get_csv_data(csvFile):
    with open(csvFile, 'r') as fin:
        reader = csv.reader(fin)
        data = list(reader)

    return data


def showImg(img, wait, windowName = 'image'):
    cv2.imshow(windowName, img)
    cv2.waitKey(wait)

def shuffleTogether(arr1, arr2, arr3, arr4):
    
    # Shuffle arrays together
    shuf = np.arange(0,len(arr1));
    np.random.shuffle(shuf);

    comb=zip(shuf,arr1);
    comb=sorted(comb);
    arr1=[x[1] for x in comb];

    comb=zip(shuf,arr2);
    comb=sorted(comb);
    arr2=[x[1] for x in comb];

    comb=zip(shuf,arr3);
    comb=sorted(comb);
    arr3=[x[1] for x in comb];

    comb=zip(shuf,arr4);
    comb=sorted(comb);
    arr4=[x[1] for x in comb];
    
    return np.array(arr1), np.array(arr2), np.array(arr3), np.array(arr4)



def getGridCellNumber(point, gridSize):
    cellSize = 1.0/float(gridSize)

    cellX = int(float(point[0])/cellSize)
    cellY = int(float(point[1])/cellSize)

    cellNumber = cellX + gridSize*cellY
    return cellNumber



def getGridLocation(cellNumber, gridSize):
    cellSize = 1.0/float(gridSize)

    cellX = (cellNumber%gridSize)*cellSize + cellSize/2.0
    cellY = (int(cellNumber/gridSize) )*cellSize + cellSize/2.0
    return [cellX,cellY]


def cropImage(img, bbox):

    height = img.shape[0]
    width = img.shape[1]
    bbox = bbox[:]
    bbox[0] = max(0, bbox[0]*width)
    bbox[2] = min(width, bbox[2]*width)
    bbox[1] = max(0, bbox[1]*height)
    bbox[3] = min(height, bbox[3]*height)

    bbox = list(map(int,bbox))
    # print(bbox)
    # return img[ bbox[1]:bbox[1]+bbox[3], bbox[0]:bbox[0]+bbox[2] ]
    new_img = np.copy(img)
    return new_img[ bbox[1]:bbox[3], bbox[0]:bbox[2] ]



"""
# generator for GazeFollow dataset
def generator(data_file):
# data_file : txt file with list of training images and their annotations

    
    data = get_csv_data(data_file)
    root_folder = '/'.join(data_file.split('/')[:-1])
    ind = 0
    num_samples = len(data)

    while True:
        
        batch_input_images = []
        batch_head_images = []
        batch_head_locations = []
        batch_gaze_locations = []

        for ii in range(ind, ind+BATCH_SIZE):

            idx = ii%num_samples
            print(data[idx])
            image_path = os.path.join(root_folder, data[idx][0])
            image_number = int(data[idx][1])
            head_bbox = list(map(float,data[idx][2:6]))
            gaze_coordinates = list(map(float,data[idx][6:8]))
            eye_coordinates = list(map(float,data[idx][8:10]))

            input_image = cv2.imread(image_path)
            head_image = cropImage(input_image, head_bbox)
            head_location = np.array(eye_coordinates).reshape(-1,1,1)
            gaze_location = getGridCellNumber(gaze_coordinates)


            batch_input_images.append(input_image)
            batch_head_images.append(head_image)
            batch_head_locations.append(head_location)
            batch_gaze_locations.append(gaze_location)


            cv2.line(input_image,(int(eye_coordinates[0]*input_image.shape[1]), int(eye_coordinates[1]*input_image.shape[0]) ), 
                (int(gaze_coordinates[0]*input_image.shape[1]) ,  int(gaze_coordinates[1]*input_image.shape[0]) ), 
                (0,50,200),4, cv2.LINE_AA)

            cv2.circle(input_image, (int(head_bbox[2]*input_image.shape[1]), int(head_bbox[3]*input_image.shape[0]) ),
             5, (0, 255, 100), 5, cv2.LINE_AA)


            showImg(input_image,0,'image')
            showImg(head_image,0,'head')

        ind+=BATCH_SIZE

        if (ind >= num_samples):
            ind = ind%num_samples;

        batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations = shuffleTogether(batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations)

        yield batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations

"""

def loadVGGImage(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    x = image.img_to_array(img)
    x = np.expand_dims(x, axis=0)
    x = preprocess_input(x)
    return x[0]


def preprocess_VGG_Imagenet(img):
    img[:,:,0] -= 124 # B
    img[:,:,1] -= 117 # G
    img[:,:,2] -= 104 # R

    return img

def preprocess_VGG_Places(img):
    img[:,:,0] -= 123 # B
    img[:,:,1] -= 117 # G
    img[:,:,2] -= 104 # R

    return img



def train_generator(data_file):
    # for VideoCoAtt dataset
    # data_file : txt file with list of training images and their annotations
    
    data = get_csv_data(data_file)
    root_folder = '/'.join(data_file.split('/')[:-1])
    ind = 0
    num_samples = len(data)
    shuffle(data)

    while True:
        
        batch_input_images = []
        batch_head_images = []
        batch_head_locations = []
        batch_gaze_locations = []

        for ii in range(ind, ind+BATCH_SIZE):

            idx = ii%num_samples
            # print(data[idx])
            image_path = os.path.join(root_folder, data[idx][2])
            image_number = int(data[idx][0])
            head_bbox = list(map(float,data[idx][7:11]))
            gaze_coordinates = list(map(float,data[idx][3:5]))
            eye_coordinates = list(map(float,data[idx][5:7]))

            # print(image_path)
            input_image = cv2.imread(image_path)
            # input_image = image.img_to_array(image.load_img(image_path, target_size=(224, 224)))
            # input_image = input_image.astype('uint8')
            # print(input_image[100:110, 100:110,:])
            head_image = cropImage(input_image, head_bbox)
            head_location = 24*to_categorical( getGridCellNumber(eye_coordinates, INTERMEDIATE_GRID_SIZE),
                                             INTERMEDIATE_GRID_SIZE*INTERMEDIATE_GRID_SIZE )
            head_location = np.array(head_location).reshape(-1,1,1)
            gaze_location = getGridCellNumber(gaze_coordinates, OUTPUT_GRID_SIZE)
            # gaze_location = to_categorical(gaze_location, )

            # image preprocessing
            input_image = cv2.resize(input_image, (INPUT_IMAGE_SHAPE[1], INPUT_IMAGE_SHAPE[0]), interpolation = cv2.INTER_AREA)
            head_image = cv2.resize(head_image, (HEAD_IMAGE_SHAPE[1], HEAD_IMAGE_SHAPE[0]))
            
            input_image = preprocess_VGG_Places(input_image.astype('float32'))
            head_image = preprocess_VGG_Imagenet(head_image.astype('float32'))

            # print(np.min(input_image), np.max(input_image))
            # print(np.min(head_image), np.max(head_image))


            batch_input_images.append(input_image)
            batch_head_images.append(head_image)
            batch_head_locations.append(head_location)
            batch_gaze_locations.append(gaze_location)

            """
            cv2.line(input_image,(int(eye_coordinates[0]*input_image.shape[1]), int(eye_coordinates[1]*input_image.shape[0]) ), 
                (int(gaze_coordinates[0]*input_image.shape[1]) ,  int(gaze_coordinates[1]*input_image.shape[0]) ), 
                (0,50,200),4, cv2.LINE_AA)

            cellLoc = getGridLocation(gaze_location, OUTPUT_GRID_SIZE)
            cv2.circle(input_image,(int(cellLoc[0]*input_image.shape[1]), int(cellLoc[1]*input_image.shape[0]) ),
                5, 
                (0,200,50),5, cv2.LINE_AA)

            showImg(input_image[:,:,2],0,'image')
            showImg(head_image,0,'head')
            """

        ind+=BATCH_SIZE

        if (ind >= num_samples):
            ind = ind%num_samples;
            shuffle(data)

        batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations = shuffleTogether(batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations)

        batch_gaze_locations = to_categorical(batch_gaze_locations, OUTPUT_GRID_SIZE*OUTPUT_GRID_SIZE)



        # convert image pixels to float [0.0 to 1.0]
        batch_head_images = np.array(batch_head_images)/255.0
        batch_input_images = np.array(batch_input_images)/255.0
        # print( 'Shapes:\n', batch_input_images.shape, batch_head_images.shape, batch_head_locations.shape, batch_gaze_locations.shape)

        yield [np.array(batch_input_images), np.array(batch_head_images), np.array(batch_head_locations)] , np.array(batch_gaze_locations)



def test_generator(data_file, doShuffle = False):
    # for VideoCoAtt dataset
    # data_file : txt file with list of training images and their annotations
    BATCH_SIZE = 1
    data = get_csv_data(data_file)
    root_folder = '/'.join(data_file.split('/')[:-1])
    ind = 0
    num_samples = len(data)

    if (doShuffle == True):
        print('Shuffling data')
        shuffle(data)
    print('')

    while True:
        
        batch_input_images = []
        batch_head_images = []
        batch_head_locations = []
        batch_gaze_locations = []

        for ii in range(ind, ind+BATCH_SIZE):

            idx = ii%num_samples
            # print(data[idx])
            image_path = os.path.join(root_folder, data[idx][2])
            image_number = int(data[idx][0])
            head_bbox = list(map(float,data[idx][7:11]))
            gaze_coordinates = list(map(float,data[idx][3:5]))
            eye_coordinates = list(map(float,data[idx][5:7]))

            # print(image_path)
            input_image = cv2.imread(image_path)
            # input_image = image.img_to_array(image.load_img(image_path, target_size=(224, 224)))
            # input_image = input_image.astype('uint8')
            # print(input_image[100:110, 100:110,:])
            head_image = cropImage(input_image, head_bbox)
            head_location = 24*to_categorical( getGridCellNumber(eye_coordinates, INTERMEDIATE_GRID_SIZE),
                                             INTERMEDIATE_GRID_SIZE*INTERMEDIATE_GRID_SIZE )
            head_location = np.array(head_location).reshape(-1,1,1)
            gaze_location = getGridCellNumber(gaze_coordinates, OUTPUT_GRID_SIZE)

            # image preprocessing
            input_image = cv2.resize(input_image, (INPUT_IMAGE_SHAPE[1], INPUT_IMAGE_SHAPE[0]), interpolation = cv2.INTER_AREA)
            head_image = cv2.resize(head_image, (HEAD_IMAGE_SHAPE[1], HEAD_IMAGE_SHAPE[0]))
            
            input_image = preprocess_VGG_Places(input_image.astype('float32'))
            head_image = preprocess_VGG_Imagenet(head_image.astype('float32'))

            # print(np.min(input_image), np.max(input_image))
            # print(np.min(head_image), np.max(head_image))


            batch_input_images.append(input_image)
            batch_head_images.append(head_image)
            batch_head_locations.append(head_location)
            batch_gaze_locations.append(gaze_location)

            """
            cv2.line(input_image,(int(eye_coordinates[0]*input_image.shape[1]), int(eye_coordinates[1]*input_image.shape[0]) ), 
                (int(gaze_coordinates[0]*input_image.shape[1]) ,  int(gaze_coordinates[1]*input_image.shape[0]) ), 
                (0,50,200),4, cv2.LINE_AA)

            cellLoc = getGridLocation(gaze_location, OUTPUT_GRID_SIZE)
            cv2.circle(input_image,(int(cellLoc[0]*input_image.shape[1]), int(cellLoc[1]*input_image.shape[0]) ),
                5, 
                (0,200,50),5, cv2.LINE_AA)

            showImg(input_image[:,:,2],0,'image')
            showImg(head_image,0,'head')
            """

        ind+=BATCH_SIZE

        if (ind >= num_samples):
            ind = ind%num_samples;
            if (doShuffle == True):
                print('Shuffling data')
                shuffle(data)

        # batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations = shuffleTogether(batch_input_images, batch_head_images, batch_head_locations, batch_gaze_locations)

        batch_gaze_locations = to_categorical(batch_gaze_locations, OUTPUT_GRID_SIZE*OUTPUT_GRID_SIZE)

        # convert image pixels to float [0.0 to 1.0]
        batch_head_images = np.array(batch_head_images)/255.0
        batch_input_images = np.array(batch_input_images)/255.0
        # print( 'Shapes:\n', batch_input_images.shape, batch_head_images.shape, batch_head_locations.shape, batch_gaze_locations.shape)
        if (ind%1000 == 0):
            print(ind,'. ', end="") 
        yield [np.array(batch_input_images), np.array(batch_head_images), np.array(batch_head_locations)] , np.array(batch_gaze_locations)




"""
mygen = train_generator('videocoatt_dataset/train_list.txt')
next(mygen)
next(mygen)
next(mygen)
next(mygen)
next(mygen)

sys.exit()
"""

def train(data_file, val_file, test_file, mode = 'train', batch_size=4, nb_epoch=10, weights = '', myLearningRate = 1e-3 ):


    # tb = TensorBoard(log_dir=os.path.join('data', 'logs', 'lstm'))

    early_stopper = EarlyStopping(monitor='loss', patience=7, verbose=1, min_delta=0.01)

    timestamp = time.time()
    currTime = time.strftime("%H-%M-%S")
    
    rm = gazefollow_keras_befOverfittingTests.GazeFollowModel( myWeights = weights, learning_rate = myLearningRate )


    # best_weights_file = os.path.join('data', 'checkpoints', 'best_'+currTime+'--{epoch:02d}.hdf5')
    best_weights_file = os.path.join('data', 'checkpoints', 'best_'+currTime+'.hdf5')

    checkpointer = ModelCheckpoint(
        best_weights_file,
        monitor='loss',
        save_weights_only=False,
        verbose=1, save_best_only=True)

    num_train_samples = len(get_csv_data(data_file))
    num_train_batches = int(num_train_samples/batch_size)

    num_val_samples = len(get_csv_data(val_file))
    # num_val_batches = int(num_val_samples/batch_size)

    if (mode == 'train'):
        hist = rm.fit_generator( 
            train_generator(data_file),
            validation_data=test_generator(val_file, doShuffle = True),
            verbose=1,
            shuffle = True,
            callbacks=[ checkpointer],
            epochs=nb_epoch*10, 
            steps_per_epoch = num_train_batches/10, 
            validation_steps = num_val_samples/50
            )



        print ('Training history:');
        PV(sorted(hist.history.items()))

    # PREDICT TEST OUTPUT
    num_test_samples = len(get_csv_data(test_file))
    # num_test_batches = int(num_test_samples/batch_size)


    print('Number of test samples :', num_test_samples)


    # loss, accuracy = rm.evaluate_generator( test_generator(test_file), steps = num_test_samples)

    # print ('Test Loss:',loss, '\n','Test Accuracy:',accuracy,'\n')

    predictions = rm.predict_generator( test_generator(test_file), steps = num_test_samples, verbose = 1)
    y_pred = np.argmax(predictions, axis=1)

    y_test = [] 
    testGen = test_generator(test_file)
    # for idx in range(len(y_pred)):
    for idx in range(num_test_samples):
        X_, Y_ = next(testGen)
        y_test.append(Y_[0])
    y_test=np.array(y_test)

    y_test = np.argmax(y_test,axis=1)

    cm = confusion_matrix(y_test,y_pred)
    print('\nConfusion Matrix:\n', cm)

    print(classification_report(y_test, y_pred))




    """
    # write training history to file

    trainCsv.write('\n');

    for key, val in sorted(hist.history.items()):
        trainCsv.write(key+',');

        for x in val:
            trainCsv.write(str(x)+',');

        trainCsv.write('\n');

    """

    """
    print ('Loading :', best_weights_file)
    rm.model.load_weights(best_weights_file)

    

#-------------------------------------------------------------------------------------------------------------------------
    # PREDICT TEST OUTPUT
#-------------------------------------------------------------------------------------------------------------------------

    # predictions = rm.model.predict(X_test)


    num_test_samples = len(X_test)
    predictions = rm.model.predict_generator( generator_test(X_test,y_test), steps = num_test_samples)


    # loss, accuracy = rm.model.evaluate(X_test, y_test)
    loss, accuracy = rm.model.evaluate_generator( generator_test(X_test,y_test), steps = num_test_samples)
    
    print ('Test Loss:',loss, '\n','Test Accuracy:',accuracy,'\n')
    
    # print confusion matrix
    y_pred = np.argmax(predictions, axis=1)
    
    trainCsv.write('\n\n')
    
    weighted_acc = 0;
    for ix in range(2):
        total_instances = confusion_matrix(np.argmax(y_test,axis=1),y_pred)[ix].sum();
        print(ix, CLASSES[ix], total_instances, confusion_matrix(np.argmax(y_test,axis=1),y_pred)[ix][ix]/float(total_instances) )
        weighted_acc+=confusion_matrix(np.argmax(y_test,axis=1),y_pred)[ix][ix]/float(total_instances)
        
        trainCsv.write(str(ix)+ ','+str(CLASSES[ix])+','+ str(total_instances) +
            ','+str(confusion_matrix(np.argmax(y_test,axis=1),y_pred)[ix][ix]/float(total_instances) ) +'\n');

    print ('Best Weighted Acc : ', weighted_acc/2.0)
    trainCsv.write('Best Weighted Acc ,' +str(weighted_acc/2.0) + '\n');
    trainCsv.write('Best Loss ,' +str(loss) + '\n');


    cm = confusion_matrix(np.argmax(y_test,axis=1),y_pred)
    print(cm)

    trainCsv.write('Confusion matrix:, '+ str(cm[0][0])+',' +str(cm[0][1])+',' +str(cm[1][0])+',' +str(cm[1][1])+',' +'\n' )



    trainCsv.write('\n\nTrain,Val,Test\n');
    trainCsv.write(str(X.shape[0])+','+str(X_val.shape[0])+','+str(X_test.shape[0])+'\n');


    # print(classification_report(y_test, y_pred))

    readablePredictions = [CLASSES[x] for x in y_pred];

    trainCsv.write('\n\nTest predictions\n');

    for x in zip(data.testFiles, readablePredictions ):
        trainCsv.write(str(x[0])+','+str(x[1])+'\n');
    

    """



def visualize_output(model_path, train_file, test_file):
    model = load_model(model_path)

    layer_name = 'gaze_heatmap'
    gaze_heatmap_model = Model(inputs=model.input,
                                     outputs=model.get_layer(layer_name).output)

    layer_name = 'saliency_map_flattened'
    saliency_heatmap_model = Model(inputs=model.input,
                                     outputs=model.get_layer(layer_name).output)







    trainGen = test_generator(train_file, doShuffle = True);
    testGen = test_generator(test_file, doShuffle = True);
    
    accuracy = 0.0
    num_samples = 1000
    avgDist = 0.0
    for idx in range(num_samples):
        X, Y = next(testGen)
        perturbedX = [np.copy(X[0]), np.copy(X[1]), np.copy(X[2])]
        # shuffle(perturbedX[2][0]) # shuffle head location
        # shuffle(perturbedX[1][0]) # shuffle head image
        # shuffle(perturbedX[0][0]) # shuffle input image
        # perturbedX[2][0]*=0 # head location
        # perturbedX[1][0]*=0 # head image 
        # perturbedX[0][0]*=0 # input image
        outputGaze = model.predict(perturbedX)
        X = perturbedX

        outputGaze = outputGaze[0] # remove batch size dimension
        Y = Y[0] # remove batch size dimension
        PV( list(zip([round(xx,3) for xx in Y], [round(xx,3) for xx in outputGaze] )) )
        # print('True:', [round(xx,3) for xx in Y])
        # print('Pred:', [round(xx,3) for xx in outputGaze])
        outputGaze = np.argmax(outputGaze)
        Y = np.argmax(Y)
        if (outputGaze == Y):
            accuracy+=1

        headpos = getGridLocation( np.argmax(X[2][0]), INTERMEDIATE_GRID_SIZE)

        print('outputGaze : ',outputGaze)
        print('TrueGaze   : ',Y)
        print('headpos   : ',headpos)

        input_image = X[0][0][:]*255.0
        input_image = -1*preprocess_VGG_Imagenet(-1*input_image)
        print(input_image.shape)
        cellLoc = getGridLocation(outputGaze, OUTPUT_GRID_SIZE)
        true_cellLoc = getGridLocation(Y, OUTPUT_GRID_SIZE)

        dist = np.linalg.norm(np.array(cellLoc)-np.array(true_cellLoc))
        print('Distance : ', dist)
        avgDist+=dist
        cv2.circle(input_image,(int(cellLoc[0]*input_image.shape[1]), int(cellLoc[1]*input_image.shape[0]) ),
            6, (0,200,50),2, cv2.LINE_AA)
        cv2.circle(input_image,(int(true_cellLoc[0]*input_image.shape[1]), int(true_cellLoc[1]*input_image.shape[0]) ),
            3, (0,50,250),2, cv2.LINE_AA)
        cv2.circle(input_image,(int(headpos[0]*input_image.shape[1]), int(headpos[1]*input_image.shape[0]) ),
            5, (200,50,0),2, cv2.LINE_AA)

        # showImg(input_image, 0 , 'predicted gaze')
        cv2.imwrite('predicted_gaze.jpg', input_image)


        gaze_heatmap = gaze_heatmap_model.predict(perturbedX)[0].reshape((14,14))

        saliency_heatmap = saliency_heatmap_model.predict(perturbedX)[0].reshape((14,14))

        multiplied_heatmap = gaze_heatmap*saliency_heatmap

        print('gaze_heatmap : \n', np.min(gaze_heatmap), np.max(gaze_heatmap))
        print('saliency_heatmap : \n', np.min(saliency_heatmap), np.max(saliency_heatmap))
        print('multiplied_heatmap : \n', np.min(multiplied_heatmap), np.max(multiplied_heatmap))

        def makeOverlay(myimg, overlay_img):
            myimg = cv2.resize(myimg, (224,224), interpolation = cv2.INTER_CUBIC)
            myimg = myimg/np.max(myimg)
            myimg = np.dstack((myimg, myimg, myimg))
            myimg = myimg*overlay_img
            return myimg

        # gaze_heatmap = gaze_heatmap/np.max(gaze_heatmap)*255.0
        # saliency_heatmap = saliency_heatmap/np.max(saliency_heatmap)*255.0
        # multiplied_heatmap = multiplied_heatmap/np.max(multiplied_heatmap)*255.0

        gaze_heatmap = makeOverlay(gaze_heatmap, input_image)
        saliency_heatmap = makeOverlay(saliency_heatmap, input_image)
        multiplied_heatmap = makeOverlay(multiplied_heatmap, input_image)

        sep = np.ones((1,224,3))*255.0
        map_image = np.vstack((gaze_heatmap,sep, saliency_heatmap,sep, multiplied_heatmap))
        # map_image = cv2.resize(map_image, (224,674), interpolation = cv2.INTER_NEAREST)
        # map_image = np.dstack((map_image, map_image, map_image))

        print(map_image.shape, input_image.shape)
        output_image = np.vstack((input_image, map_image))
        cv2.imwrite('heatmaps.jpg', output_image)
        # dummy = input()

    accuracy/=float(num_samples)
    avgDist/=float(num_samples)

    print('Accuracy : ',round(accuracy,3))
    print('avgDist  : ',round(avgDist,3) )

BATCH_SIZE = 16
nb_epoch = 10
learning_rate = 1e-4
 
dropout_val_ = 0.4


def main():

        if (len(sys.argv)<5):
            print('Usage: python train_gazeFollow.py <train/test> <train_list.txt> <validate_list.txt> <test_list.txt> <weights.hdf5>')

        print ('Batch Size = ',BATCH_SIZE, '\n', 
            'No. epochs = ',nb_epoch, '\n',
            'Learning Rate = ',learning_rate, '\n',)

        mode = sys.argv[1]

        data_csv_file = sys.argv[2];
        val_file = sys.argv[3];
        test_file = sys.argv[4];

 
        weights = ""
        if (len(sys.argv)>5):
            weights = sys.argv[5];
            print ('Using pretrained weights : \n', weights)


        visualize_output(weights, data_csv_file, test_file)
        # train(data_csv_file, val_file, test_file, mode = mode,  batch_size=BATCH_SIZE, nb_epoch=nb_epoch, weights = weights , myLearningRate = learning_rate)

if __name__ == '__main__':
    main()