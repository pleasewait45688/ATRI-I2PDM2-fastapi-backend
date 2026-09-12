FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ARG OPENCV_VERSION=4.10.0

WORKDIR /opt/build
# Install dependencies
RUN apt-get -q update && apt-get install -y --no-install-recommends \
    # Generic tools
    build-essential cmake wget unzip yasm ninja-build git perl checkinstall \
    # Image I/O
    libjpeg-dev libpng-dev libtiff-dev \
    # Media I/O
    libavcodec-dev libavformat-dev libswscale-dev libswresample-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    libxvidcore-dev x264 libx264-dev libtheora-dev \
    libfaac-dev libmp3lame-dev libvorbis-dev ffmpeg \
    # OpenCore
    libopencore-amrnb-dev libopencore-amrwb-dev \
    # Cameras programming interface
    libdc1394-dev libxine2-dev libv4l-dev v4l-utils \
    # Parallelism
    libtbb-dev \
    # Python3
    python3-dev python3-numpy python3-pip\
    # Optimization 
    libatlas-base-dev gfortran \
    # Optional 
    libprotobuf-dev protobuf-compiler \
    libgphoto2-dev libeigen3-dev libhdf5-dev doxygen \
    libgoogle-glog-dev libgflags-dev \
    libxkbcommon-dev libdbus-1-dev libffi-dev libwebp-dev\
    && apt-get autoremove \
    && rm -rf /var/cache/apt/archives /var/lib/apt/lists/* 

RUN wget -q --no-check-certificate https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip -O opencv.zip \
    && wget -q --no-check-certificate https://github.com/opencv/opencv_contrib/archive/${OPENCV_VERSION}.zip -O opencv_contrib.zip \
    && unzip -qq opencv.zip -d /opt && rm -rf opencv.zip \
    && unzip -qq opencv_contrib.zip -d /opt && rm -rf opencv_contrib.zip \
    && cmake -GNinja \
    -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=$(python3 -c "import sys; print(sys.prefix)") \
    # -D CMAKE_PREFIX_PATH=/opt/qt/${QT_VERSION}/gcc_64/ \
    -D OPENCV_EXTRA_MODULES_PATH=/opt/opencv_contrib-${OPENCV_VERSION}/modules \
    -D OPENCV_PYTHON3_INSTALL_PATH=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
    -D PYTHON_EXECUTABLE=$(which python3) \
    -D EIGEN_INCLUDE_PATH=/usr/include/eigen3 \
    -D OPENCV_ENABLE_NONFREE=ON \
    -D WITH_CUDA=ON \
    -D CUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda-12.1 \
    -D CUDA_FAST_MATH=1 \
    -D ENABLE_FAST_MATH=1 \
    -D WITH_CUDNN=ON \
    # -D CUDA_ARCH_BIN=7.5 \
    -D CUDA_ARCH_BIN=8.9 \
    -D OPENCV_DNN_CUDA=ON \
    -D WITH_CUBLAS=1 \
    -D BUILD_opencv_cudacodec=OFF \
    -D WITH_OPENGL=ON \
    -D OpenGL_GL_PREFERENCE=LEGACY \
    -D WITH_EIGEN=ON \
    -D WITH_TBB=ON \
    -D WITH_LAPACK=ON \
    -D WITH_PROTOBUF=ON \
    -D WITH_V4L=ON \
    -D WITH_QT=ON \
    -D WITH_FFMPEG=ON \
    -D WITH_VTK=OFF \
    -D WITH_OPENEXR=OFF \
    -D WITH_OPENCL=OFF \
    -D WITH_OPENNI=OFF \
    -D WITH_XINE=OFF \
    -D WITH_GDAL=OFF \
    -D WITH_IPP=OFF \
    -D BUILD_OPENCV_PYTHON3=ON \
    -D BUILD_OPENCV_JAVA=OFF \
    -D BUILD_TESTS=OFF \
    -D BUILD_IPP_IW=OFF \
    -D BUILD_PERF_TESTS=OFF \
    -D BUILD_EXAMPLES=OFF \
    -D BUILD_ANDROID_EXAMPLES=OFF \
    -D BUILD_DOCS=OFF \
    -D BUILD_ITT=OFF \
    -D INSTALL_PYTHON_EXAMPLES=OFF \
    -D INSTALL_C_EXAMPLES=OFF \
    -D INSTALL_TESTS=OFF \
    /opt/opencv-${OPENCV_VERSION} \
    && ninja \
    && ninja install \
    && rm -rf /opt/build/* \
    && rm -rf /opt/opencv-${OPENCV_VERSION} \
    && rm -rf /opt/opencv_contrib-${OPENCV_VERSION}

COPY ./requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip3 install --upgrade pip \ 
    && pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 \
    # && pip3 install cython \
    && pip3 install -r requirements.txt


# Install mplfonts and initialize it ==> for chinese font
RUN pip3 install -U mplfonts && mplfonts init

WORKDIR /i2pdm2/

COPY ./app app
# Model weights ship as real files in app/pest/model/ (see app/pest/model/README) — no network download needed.

# CMD ["fastapi", "run", "--workers", "4", "app/main.py"]