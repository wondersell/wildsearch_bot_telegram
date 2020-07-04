def image_bag(number, image_pale, image_bright, maximum=5):
    images = []

    full_images = int(number)
    empty_images = maximum - full_images  # У нас пятибальная шкала

    for _ in range(1, full_images + 1):
        images.append(image_bright)

    for _ in range(1, empty_images + 1):
        images.append(image_pale)

    return images
