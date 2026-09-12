# Model weights

Not tracked in git (see `.gitignore`). Place these files here before `docker build` — the
Dockerfile just `COPY`s this directory, it no longer downloads anything:

- `best.pt` — YOLOv11 detector
- `resnet18_best_model_513d.pth` — ResNet18 classifier
- `labels.json` — classifier labels
- `svm_cifar_100.pickle` — SVM quality-inspection model

Deliver these as real files alongside the project (e.g. secure file transfer), not via a link.
