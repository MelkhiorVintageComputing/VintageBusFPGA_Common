/*%
  flashsend -- Flash memory uploade
  Copyright (C) 2009-2017 ZTEX GmbH.
  http://www.ztex.de
  Copyright (C) 2023 Romain Dolbeau <romain@dolbeau.org>

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
  %*/

import java.io.*;
import java.util.*;
import java.nio.*;

import org.usb4java.*;

import ztex.*;

// *****************************************************************************
// ******* ParameterException **************************************************
// *****************************************************************************
// Exception the prints a help message
class ParameterException extends Exception {
    public final static String helpMsg = new String (
													 "Parameters:\n"+
													 "    -d <number>   Device Number (default: 0)\n" +
													 "    -n <number>   Sector to start read/writing from/to\n" +
													 "    -f <name>     File to read/write\n" +
													 "    -w            Write instead of read\n" +
													 "    -s <number>   How many bytes to read\n" + 
													 "    -p            Print bus info\n" +
													 "    -h            This help" );
    
    public ParameterException (String msg) {
		super( msg + "\n" + helpMsg );
    }
}

// *****************************************************************************
// ******* Test0 ***************************************************************
// *****************************************************************************
class FlashSend extends Ztex1v1 {

	// ******* FlashSend **********************************************************
	// constructor
    public FlashSend ( ZtexDevice1 pDev ) throws UsbException {
		super ( pDev );
    }
	
	// ******* doRead **************************************************************
	// write the file 
    public void doRead (int sector, int size, File f) throws UsbException, InvalidFirmwareException, CapabilityException, FileNotFoundException, IOException, ParameterException {
		int flashSectorSize = flashSectorSize();
		long totalSec = (size + flashSectorSize - 1) / flashSectorSize;
		long bufLen = totalSec * flashSectorSize;
		byte[] filedata = new byte[(int)bufLen]; 
		//FileInputStream fis = new FileInputStream(f);
		//fis.read(filedata); 
		//fis.close();
		int secNum = Math.max(1, 2048 / flashSectorSize );
		byte[] wBuf = new byte[flashSectorSize * secNum];
		long i;

		if ((sector + totalSec) > flashSectors()) {
			throw new ParameterException("File request too large");
		}

		System.out.println("Going to read the file '" + f.getName() + "' of size " + size + " bytes to " + totalSec + " sector(s) at offset " + sector + "");

		long t0 = new Date().getTime();

		for (i = 0 ; i < totalSec ; i += secNum) {
			int j = Math.min((int)(totalSec - i), secNum);
			System.out.println("Sector " + (i+j) + "/" + totalSec + "  " + Math.round(10000.0*(i+j)/totalSec)/100.0 + "% (" + secNum + " sector(s))");
			flashReadSector((int)(sector + i), j, wBuf);
			System.arraycopy(wBuf,0,filedata,(int)(flashSectorSize*i),flashSectorSize*j);
		}
			
		t0 = new Date().getTime() - t0;

		System.out.println("Reading " + size + " bytes (" + totalSec + " sectors) took " + t0 + " millisecons");

		FileOutputStream fis = new FileOutputStream(f);
		fis.write(filedata, 0, size); 
		fis.close();
    }

	// ******* doWrite **************************************************************
	// write the file 
    public void doWrite (int sector, File f ) throws UsbException, InvalidFirmwareException, CapabilityException, FileNotFoundException, IOException, ParameterException {
		int flashSectorSize = flashSectorSize();
		long totalSec = (f.length() + flashSectorSize - 1) / flashSectorSize;
		long bufLen = totalSec * flashSectorSize;
		byte[] filedata = new byte[(int)bufLen]; 
		FileInputStream fis = new FileInputStream(f);
		fis.read(filedata); 
		fis.close();
		int secNum = Math.max(1, 2048 / flashSectorSize );
		byte[] wBuf = new byte[flashSectorSize * secNum];
		long i;

		if ((sector + totalSec) > flashSectors()) {
			throw new ParameterException("File won't fit");
		}

		System.out.println("Going to write the file '" + f.getName() + "' of size " + f.length() + " bytes to " + totalSec + " sector(s) at offset " + sector + "");

		long t0 = new Date().getTime();

		for (i = 0 ; i < totalSec ; i += secNum) {
			int j = Math.min((int)(totalSec - i), secNum);
			System.arraycopy(filedata,(int)(flashSectorSize*i),wBuf,0,flashSectorSize*j);
			System.out.println("Sector " + (i+j) + "/" + totalSec + "  " + Math.round(10000.0*(i+j)/totalSec)/100.0 + "% (" + secNum + " sector(s))");
			flashWriteSector((int)(sector + i), j, wBuf);
		}
			
		t0 = new Date().getTime() - t0;

		System.out.println("Writing " + f.length() + " bytes (" + totalSec + " sectors) took " + t0 + " millisecons");
    }

	// ******* main ****************************************************************
    public static void main (String args[]) {
    
		int devNum = 0;
		int sector = -1; // fail as default
		String filename = null;
		boolean doRead = true, doWrite = false;
		int size = -1;

		if ( ! System.getProperty("os.name").equalsIgnoreCase("linux") ) {
			Runtime.getRuntime().addShutdownHook(new Thread() {
					public void run() { 
						Scanner s=new Scanner(System.in);
						System.out.println("Press <enter> to continue ...");
						s.nextLine();
					}
				});	
		}

		try {
			// Scan the USB. This also creates and initializes a new USB context.
			ZtexScanBus1 bus = new ZtexScanBus1( ZtexDevice1.ztexVendorId, ZtexDevice1.ztexProductId, true, false, 1);
	    
			// scan the command line arguments
    	    for (int i=0; i<args.length; i++ ) {
				if ( args[i].equals("-d") ) {
					i++;
					try {
						if (i>=args.length) throw new Exception();
						devNum = Integer.parseInt( args[i] );
					} 
					catch (Exception e) {
						throw new ParameterException("Device number expected after -d");
					}
				}
				else if ( args[i].equals("-n") ) {
					i++;
					try {
						if (i>=args.length) throw new Exception();
						sector = Integer.parseInt( args[i] );
					} 
					catch (Exception e) {
						throw new ParameterException("Offset expected after -n");
					}
				}
				else if ( args[i].equals("-f") ) {
					i++;
					try {
						if (i>=args.length) throw new Exception();
						filename = args[i];
					} 
					catch (Exception e) {
						throw new ParameterException("Filename expected after -p");
					}
				}
				else if ( args[i].equals("-s") ) {
					i++;
					try {
						if (i>=args.length) throw new Exception();
						size = Integer.parseInt( args[i] );
					} 
					catch (Exception e) {
						throw new ParameterException("Size expected after -s");
					}
				}
				else if ( args[i].equals("-w") ) {
					doRead = false;
					doWrite = true;
				}
				else if ( args[i].equals("-p") ) {
					bus.printBus(System.out);
					System.exit(0);
				}
				else if ( args[i].equals("-h") ) {
					System.err.println(ParameterException.helpMsg);
					System.exit(0);
				}
				else throw new ParameterException("Invalid Parameter: "+args[i]);
			}
	    

			// create the main class	    
			if ( bus.numberOfDevices() <= 0) {
				System.err.println("No devices found");
				System.exit(0);
			}
			FlashSend ztex = new FlashSend ( bus.device(devNum) );
			bus.unref();
	    
			// print some information
			System.out.println("Capabilities: " + ztex.capabilityInfo(", "));
	    
			if ( ztex.interfaceCapabilities(CAPABILITY_FLASH) ) {
				System.out.println("Primary Flash enabled: " + ztex.flashEnabled());
				System.out.println("Primary Flash sector size: " + ztex.toHumanStr(ztex.flashSectorSize())+" Bytes");
				System.out.println("Primary Flash size: " + ztex.toHumanStr(ztex.flashSize())+" Bytes");
			} else {
				throw new ParameterException("Currently write only to Primary Flash, which is not available.");
			}

			if ( ztex.interfaceCapabilities(CAPABILITY_FLASH2) ) {
				System.out.println("Secondary Flash enabled: " + ztex.flash2Enabled());
				System.out.println("Secondary Flash sector size: " + ztex.toHumanStr(ztex.flash2SectorSize())+" Bytes");
				System.out.println("Secondary Flash size: " + ztex.toHumanStr(ztex.flash2Size())+" Bytes");
			}
			
			if (sector < 0) {
				throw new ParameterException("Sector to start must be specified as a positive integer, it is recommened to be higher than the reserved area.");
			}
	    
			if (filename == null) {
				throw new ParameterException("Non-existent filename: " + (filename == null ? "(null)": "filename" ));
			}

			if (doWrite) {
				File f = new File(filename);
				if (!f.exists() || !f.isFile() || !f.canRead() || f.length() == 0) {
					throw new ParameterException("Impossible to access specific filename: " + (filename == null ? "(null)": "filename" ));
				}
				if (f.length() > (16*1024*1024)) {
					throw new ParameterException("File seems too large at " + f.length() + "bytes." );
				}
				
				ztex.doWrite(sector, f);
			}
			else if (doRead) {
				File f = new File(filename);
				if (f.exists()) {
					throw new ParameterException("File '" + filename + "' exists, overwrite not supported.\n");
				}
				if (size <= 0) {
					throw new ParameterException("Can't read " + size + "bytes");
				}
				
				ztex.doRead(sector, size, f);
			}
			
			// release resources
			ztex.dispose();
    
		}
		catch (Exception e) {
			System.out.println("Error: "+e.getLocalizedMessage() );
		} 
	} 
   
}
