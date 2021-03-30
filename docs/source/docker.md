# Docker course

https://app.pluralsight.com/course-player?clipId=2abb82d1-2e6b-4441-8cf7-d51827827dfc

## Intro

Namespace isolation + Control 

## Working with images

Stored in a registry (in house or cloud)

Image Manifest describes layers of the image

```bash
docker image pull redis #same as docker image pull docker.io/redis/latest
docker history redis
docker image inspect redis
docker image rm redis

docker image ls --digests
```

## Registries

default:DOCKER HUB:docker.io

On-premise registries: Docker Trusted Registry (DTR)

```bash
docker image pull docker.io/redis/latest # Registry/Repo/Image (tag)
```

latest does not mean actually latest (images are tagged manually as latest)

Content hash -> hash of container layer

When pushing to registry we compress layers, then we have Distribution hashes for verification

Upload to a registry

```bash
docker image push xxx
```

You should put Dockerfile in the root folder of your app

## Multi-stage Builds

Useful for production environments.

## check running processes

```bash
ps -elf
docker container run -d alpine sleep 1d
docker container exec -it <container> sh
```

## Example app

```bash
docker image build -t psweb https://github.com/nigelpoulton/psweb.git
docker container run -d --name web1 -p 8080:8080 psweb  
docker container stop web1 
docker container rm web1 
```

## Default processes for new containers

```
CMD: Run-time arguments override CMD instructions
ENTRYPOINT: Run-time arguments are appended to ENTRYPOINT
```

## get the list of the port mappings

```bash
docker port web1
```

## Remove all containers (-f forces the operation)

```bash
docker container rm  $(docker container ls -aq) -f
```

## Logging (STDOUT | STDERR are forwarded to logging driver, e.g. standard daemon.sjon)

```bash
docker logs <container>
```

## Building a secure swarm

```bash
docker system info

docker swarm init
docker node ls
docker swarm join-token manager #gives a join command for another node
```

## Container networking

### Bridge Networking - most common (the worst)

Bridge or docker0 is the default bridge network

```docker network create -d bridge golden-gate```

### Overlay Networking

```bash
docker network create -o encrypted
docker network create -d overlay overnet
```

### Macvlan

Must allow promiscuous mode

```bash
docker network ls
docker network inspect bridge
```

## Working with volumes and persistent data

```bash
docker volume create gbvol 
docker volume ls
docker volume inspect gbvol 
```

## Working with secrets

Requires swarm mode
