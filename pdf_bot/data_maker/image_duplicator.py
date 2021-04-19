import cv2


temp1 = "AFT_søknad_4"
temp2 = "Avklaring_søknad_1"
temp3 = "Oppfølging_søknad_1"

file = "/home/swapnil/projects/object_detection_project/Tensorflow/workspace/training_demo/labeled_images/fretext_images_to_train/duplicator_folder/AFT_søknad_4.jpg"
im = cv2.imread(file)
n = 10
for i in range(6:n+6-1):
	new_name = temp1 + "_" + i
	cv2.imwrite(new_name ,im)