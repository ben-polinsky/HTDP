# HTDP
Horizontal Time-Dependent Positioning (HTDP) is a utility that allows users to transform positional coordinates across time and between spatial reference frames.

HTDP (Horizontal Time-Dependent Positioning) enables users to estimate horizontal displacements and/or horizontal velocities related to crustal motion in the United States and its territories.  The utility also enables users to update positional coordinates and/or geodetic observations to a user-specified date.  HTDP supports these activities for coordinates in the North American Datum of 1983 (NAD 83) as well as in all official realizations of the International Terrestrial Reference System (ITRS) and all official realizations of the World Geodetic System of 1984 (WGS 84).  Accordingly, HTDP may be used to transform positional coordinates between any pair of these reference frames in a manner that rigorously addresses differences in the definitions of their respective velocity fields.  HTDP may also be used to transform velocities between any pair of these reference frames.

For additional information, contact:
NOAA National Geodetic Survey,
ngs.infocenter@noaa.gov

Visit:
https://geodesy.noaa.gov/TOOLS/Htdp/Htdp.shtml

## NOAA Open Source Disclaimer

This repository is a scientific product and is not official communication of the National Oceanic and Atmospheric Administration, or the United States Department of Commerce. All NOAA GitHub project code is provided on an ?as is? basis and the user assumes responsibility for its use. Any claims against the Department of Commerce or Department of Commerce bureaus stemming from the use of this GitHub project will be governed by all applicable Federal law. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation or favoring by the Department of Commerce. The Department of Commerce seal and logo, or the seal and logo of a DOC bureau, shall not be used in any manner to imply endorsement of any commercial product or activity by DOC or the United States Government.

Please note that there is no confidentiality on any code submitted through pull requests to NOAA National Geodetic Survey. If the pull requests are accepted and merged into the master branch then they become part of publicly accessible code. 

## License

Software code created by U.S. Government employees is not subject to copyright in the United States (17 U.S.C. �105). The United States/Department of Commerce reserve all rights to seek and obtain copyright protection in countries other than the United States for Software authored in its entirety by the Department of Commerce. To this end, the Department of Commerce hereby grants to Recipient a royalty-free, nonexclusive license to use, copy, and create derivative works of the Software outside of the United States.

## IMPORTANT NOTICE
*** HTDP should NOT be used to transform between NAD 83 realizations (2011, NSRS2007, HARN, etc.). It will not give correct results. To transform between NAD 83 realizations, use the NGS Coordinate Conversion and Transformation Tool (NCAT) instead. ***

## Containerised web service

This repository now includes a minimal REST API that wraps the interactive HTDP
binary and exposes it as a web service. The service is implemented with
[FastAPI](https://fastapi.tiangolo.com/) and can be built directly from the
provided `Dockerfile`.

### Build and run locally

```
docker build -t htdp-service .
docker run --rm -p 8080:8080 htdp-service
```

Once the container is running you can explore the API documentation at
<http://localhost:8080/docs>.

The service provides the following endpoints:

* `GET /health` – readiness probe returning `{ "status": "ok" }` when the
  service is available.
* `GET /frames` – list of reference-frame menu options that mirror HTDP's
  interactive menu.
* `POST /transform` – transform one or more positions. Supply a JSON payload of
  the form:

  ```json
  {
    "input_frame": "ITRF2014 or IGS14/IGb14",
    "output_frame": "ITRF2020 or IGS20/IGb20",
    "input_epoch": 2010.0,
    "output_epoch": 2020.0,
    "points": [
      {
        "name": "EXAMPLE",
        "latitude": 40.0,
        "longitude": -105.0,
        "ellipsoid_height": 1500.0
      }
    ]
  }
  ```

  Longitudes should follow the conventional GIS convention of positive-east; the
  service handles conversion to the positive-west convention expected by HTDP.

### Deploy to Fly.io

The repository includes a starter `fly.toml` configuration. Update the `app`
value to match your Fly.io application name and then deploy:

```
fly auth login
fly launch --no-deploy  # optional, to inspect or tweak settings
fly deploy
```

The service listens on port 8080 internally; Fly will expose it on the
allocated public address.

