from conans import ConanFile
import os, shutil
from conans.tools import download, unzip, replace_in_file, check_md5
from conans import CMake, tools

import sys

class GnutlsConan(ConanFile):
    name = "gnutls"
    version = "3.4.16"
    generators = "cmake"
    settings =  "os", "compiler", "arch"
    options = {"shared": [True, False],
               "enable_m_guard": [True, False],
               "disable_asm": [True, False],
               "enable_ld_version_script": [True, False],
               "disable_endian_check": [True, False],
               "enable_random_daemon": [True, False],
               "enable_hmac_binary_check": [True, False],
               "disable_padlock_support": [True, False],
               "disable_aesni_support": [True, False],
               "disable_O_flag_munging": [True, False]}
               #TODO add in non-binary flags
    requires = (
        'libiconv/1.14@lasote/stable',
        'nettle/3.3@DEGoodmanWilson/testing',
        'gmp/6.1.1@DEGoodmanWilson/testing',
        'zlib/1.2.8@lasote/stable'
    )
    # TODO add p11-kit http://p11-glue.freedesktop.org/p11-kit.html and libidn and libdane

    url = "http://github.com/DEGoodmanWilson/conan-gnutls"
    default_options = "shared=False", "enable_m_guard=False", "disable_asm=False", \
                      "enable_ld_version_script=False", "disable_endian_check=False", \
                      "enable_random_daemon=False", "disable_aesni_support=False", \
		      "enable_hmac_binary_check=False", "disable_padlock_support=False", "disable_O_flag_munging=False"

    ZIP_FOLDER_NAME = "gnutls-%s" % version

    def source(self):
        zip_name = "gnutls-%s.tar.xz" % self.version
#        download("ftp://ftp.gnutls.org/gcrypt/gnutls/v3.4/%s" % zip_name, zip_name)
        self.download_ftp("ftp://ftp.gnutls.org/gcrypt/gnutls/v3.4/%s" % zip_name, zip_name)
        tools.check_sha256(zip_name, "d99abb1b320771b58c949bab85e4b654dd1e3e9d92e2572204b7dc479d923927")
        #tools.untargz(zip_name)
        self.uncompress_xz(zip_name)

    def uncompress_xz(self, filename):
        try:
            self.uncompress_xz_3_3(filename)
            return
        except:
            self.output.info("Could not uncompress with tarfile, maybe not running on python >=3.3")
        
        try:
            self.uncompress_lzma(filename)
            return
        except:
            self.output.info("Failed to uncompress with lzma library")
            
        self.output.info("try running tar")
        
        self.uncompress_tar(filename)
        
    def uncompress_xz_3_3(self, filename):
        import tarfile

        with tarfile.open(filename) as f:
            f.extractall('.')
            
    def uncompress_lzma(self, filename):
        import contextlib
        import lzma
        import tarfile
        
        with contextlib.closing(lzma.LZMAFile('test.tar.xz')) as xz:
            with tarfile.open(fileobj=xz) as f:
                f.extractall('.')
                
    def uncompress_tar(self, filename):
        cmd = "tar xvfJ " + filename
        self.output.info(cmd)
        self.run(cmd) 
        
    def config(self):
        del self.settings.compiler.libcxx

    def generic_env_configure_vars(self, verbose=False):
        """Reusable in any lib with configure!!"""
	
        # find nettle and hogweed paths
        nettle_lib_path = ""
        nettle_include_path = ""
        gmp_lib_path = ""
        gmp_include_path = ""
        for path in self.deps_cpp_info.lib_paths:
            if "nettle" in path:
                nettle_lib_path = path
            elif "gmp" in path:
                gmp_lib_path = path

        for path in self.deps_cpp_info.include_paths:
            if "nettle" in path:
                nettle_include_path = path
            elif "gmp" in path:
                gmp_include_path = path


        if self.settings.os == "Linux" or self.settings.os == "Macos":
            libs = 'LIBS="%s"' % " ".join(["-l%s" % lib for lib in self.deps_cpp_info.libs])
            ldflags = 'LDFLAGS="%s -liconv"' % " ".join(["-L%s" % lib for lib in self.deps_cpp_info.lib_paths]) 
            archflag = "-m32" if self.settings.arch == "x86" else ""
            cflags = 'CFLAGS="-fPIC %s %s %s"' % (archflag, " ".join(self.deps_cpp_info.cflags), " ".join(['-I"%s"' % lib for lib in self.deps_cpp_info.include_paths]))
            cpp_flags = 'CPPFLAGS="%s %s %s"' % (archflag, " ".join(self.deps_cpp_info.cppflags), " ".join(['-I"%s"' % lib for lib in self.deps_cpp_info.include_paths]))
            package_flags = 'NETTLE_CFLAGS="-I%s" NETTLE_LIBS="-L%s -lnettle" HOGWEED_CFLAGS="-I%s" HOGWEED_LIBS="-L%s -lhogweed" GMP_CFLAGS="-I%s" GMP_LIBS="-L%s -lgmp"' % (nettle_include_path, nettle_lib_path, nettle_include_path, nettle_lib_path, gmp_include_path, gmp_lib_path)
            command = "env %s %s %s %s %s" % (libs, ldflags, cflags, cpp_flags, package_flags)
        elif self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            cl_args = " ".join(['/I"%s"' % lib for lib in self.deps_cpp_info.include_paths])
            lib_paths= ";".join(['"%s"' % lib for lib in self.deps_cpp_info.lib_paths])
            command = "SET LIB=%s;%%LIB%% && SET CL=%s" % (lib_paths, cl_args)
            if verbose:
                command += " && SET LINK=/VERBOSE"


        return command
       
    def build(self):
        if self.settings.os == "Windows":
            self.output.fatal("Cannot build on Windows, sorry!")
            return # no can do boss!

        self.build_with_configure()
            
        
    def build_with_configure(self):
        config_options_string = ""

        for option_name in self.options.values.fields:
            activated = getattr(self.options, option_name)
            if activated:
                self.output.info("Activated option! %s" % option_name)
                config_options_string += " --%s" % option_name.replace("_", "-")

        iconv_prefix = ""
        for path in self.deps_cpp_info.lib_paths:
            if "iconv" in path:
                iconv_prefix = '/lib'.join(path.split("/lib")[0:-1]) #remove the final /lib. There are probably better ways to do this.
                break

        env_vars = self.generic_env_configure_vars()

        # TODO remove --without-p11-kit
        build_options = ' '.join([
            "--enable-static",
            "--enable-shared",
            "--without-p11-kit",
            "--with-included-libtasn1",
            "--enable-local-libopts",
            "--with-libiconv-prefix=" + iconv_prefix
        ])

        configure_command = "%s ./configure %s %s" % (env_vars, build_options, config_options_string)
        self.output.warn(configure_command)
        self.run(configure_command, cwd=self.ZIP_FOLDER_NAME)

        self.run("make", cwd=self.ZIP_FOLDER_NAME)

    def package(self):
        if self.settings.os == "Windows":
            self.output.fatal("Cannot build on Windows, sorry!")
            return

        self.copy("*.h", dst="include", src="%s/src" % (self.ZIP_FOLDER_NAME), keep_path=True)
        self.copy("*.h", dst="include", src="%s/lib/includes" % (self.ZIP_FOLDER_NAME), keep_path=True)
        if self.options.shared:
            self.copy(pattern="*.so*", dst="lib", src=self.ZIP_FOLDER_NAME, keep_path=False)
            self.copy(pattern="*.dll*", dst="bin", src=self.ZIP_FOLDER_NAME, keep_path=False)
        else:
            self.copy(pattern="*.a", dst="lib", src="%s" % self.ZIP_FOLDER_NAME, keep_path=False)
        
        self.copy(pattern="*.lib", dst="lib", src="%s" % self.ZIP_FOLDER_NAME, keep_path=False)
        
    def package_info(self):
        self.cpp_info.libs = ['gnutls']


    def download_ftp(self, url, filename):
        self.output.info("downloading ftp file from url: " + url)
        
        from ftplib import FTP, FTP_TLS
        from urlparse import urlparse

        u = urlparse(url)

        host = u.netloc
        paths = u.path.split("/")
        url_filename = paths[-1]
        paths = paths[ : -1]

#        try:
#            ftp = FTP_TLS(host)
#        except:
#            ftp = FTP(host)
        ftp = FTP(host)

        ftp.login()

        if paths:
            ftp.cwd('/'.join(paths))

        file = open(filename, 'wb')
        ftp.retrbinary('RETR %s' % url_filename, file.write)
